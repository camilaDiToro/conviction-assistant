"""Acceptance test for search_convictions over the real conviction corpus.

Reads `tests/fixtures/retrieval_golden.yaml` (29 cases drafted with Claude Opus assistance, across
literal / topic / cross_lang buckets in PT/EN/ES), ingests the real
`convictions/` directory once, and asserts per-bucket recall@5 floors:

- literal    >= 90%   (BM25 is decisive on literal queries)
- topic      >= 50%   (loose floor; paraphrase recall is what hybrid lifts)
- cross_lang  reported-only (canary — fixture-flagged BM25-hostile)
- p95 latency < 50 ms — measured around the **BM25Retriever.search** call only,
  not the full `await search_convictions(...)` wrapper. The wrapper adds
  PassageHit construction + snippet generation that we don't want masking
  a retrieval regression. Tool-level p95 is reported alongside but doesn't
  gate. A 5-query warm-up settles bm25s caches before the timed loop.

The gates are **provisional**. Cross_lang failures are expected given
v1's BM25-only stack; surfacing them is the trigger for a future hybrid-
retrieval step.
"""

from collections import defaultdict
from pathlib import Path

import pytest
import yaml

from app.agent.tools import ToolContext, search_convictions
from app.config import db
from app.errors import EmptyQueryError
from app.retrieval.bm25 import BM25Retriever
from app.services.ingest import ingest_corpus

REPO_ROOT = Path(__file__).resolve().parents[3]
CONVICTIONS_DIR = REPO_ROOT / "convictions"
GOLDEN_PATH = REPO_ROOT / "tests" / "fixtures" / "retrieval_golden.yaml"
K = 5
P95_LATENCY_MS = 50.0
BUCKET_FLOORS: dict[str, float] = {
    "literal": 0.90,
    "topic": 0.50,
    # cross_lang is reported but not gated — see module docstring.
}


@pytest.fixture(scope="module")
async def ctx_for_real_corpus(tmp_path_factory):
    """Ingest the real convictions/ once; build the BM25 index; yield a
    ToolContext bound to that session + index. Module-scoped so we run the
    ~30-doc parse + index build once per pytest invocation.
    """
    tmp_path = tmp_path_factory.mktemp("search_acceptance")
    db_path = tmp_path / "search.sqlite"
    db.migrate(db_path)
    engine = db.make_engine(f"sqlite+aiosqlite:///{db_path.as_posix()}")
    factory = db.make_session_factory(engine)

    async with factory() as session:
        await ingest_corpus(session, CONVICTIONS_DIR)
        index = BM25Retriever()
        await index.build(session)
        yield ToolContext(session=session, retriever=index)

    await engine.dispose()


def _percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    k = max(0, min(len(sorted_vals) - 1, int(round((p / 100.0) * (len(sorted_vals) - 1)))))
    return sorted_vals[k]


async def test_retrieval_golden(ctx_for_real_corpus, capsys):
    """Score every fixture case under TWO rules:

    - **primary**: 1 if expected_passage_ids[0] is in top-k, else 0. This is the gate.
    - **weighted**: 1.0 if primary in top-k, 0.5 if any secondary in top-k, else 0.0.

    Both numbers are printed per bucket. Only `primary` gates per-bucket floors.
    """
    cases = yaml.safe_load(GOLDEN_PATH.read_text(encoding="utf-8"))["cases"]
    assert cases, "golden fixture is empty"

    import time

    index = ctx_for_real_corpus.retriever
    # Warm up bm25s caches so the first few timed cases don't skew p95 on
    # this 29-sample run. Queries chosen to hit different docs.
    for warm_q in ("CDB", "fundos imobiliarios", "private equity", "renda fixa", "ETF"):
        index.search(warm_q, k=K)

    # (case_id, bucket, primary_passed, weighted_score, index_ms, tool_ms)
    results: list[tuple[str, str, bool, float, float, float]] = []
    for case in cases:
        expected = case["expected_passage_ids"]
        primary = expected[0]
        secondaries = expected[1:]
        # Index-only timing — what the p95 gate is meant to measure.
        ti = time.perf_counter()
        index.search(case["query"], k=K)
        dt_index_ms = (time.perf_counter() - ti) * 1000.0
        # Tool-level timing — reported as overhead headroom, doesn't gate.
        tt = time.perf_counter()
        hits = await search_convictions(ctx_for_real_corpus, query=case["query"], k=K)
        dt_tool_ms = (time.perf_counter() - tt) * 1000.0
        ids_returned = [h.passage_id for h in hits]
        primary_passed = primary in ids_returned
        if primary_passed:
            weighted = 1.0
        elif any(sec in ids_returned for sec in secondaries):
            weighted = 0.5
        else:
            weighted = 0.0
        results.append(
            (case["id"], case["bucket"], primary_passed, weighted, dt_index_ms, dt_tool_ms)
        )

    # Per-bucket aggregation: (passed, weighted, dt_index, dt_tool)
    by_bucket: dict[str, list[tuple[bool, float, float, float]]] = defaultdict(list)
    for _, bucket, passed, weighted, dt_i, dt_t in results:
        by_bucket[bucket].append((passed, weighted, dt_i, dt_t))

    # Print breakdown — visible with pytest -s; on failure, pytest also dumps stdout.
    lines = ["", f"=== retrieval_golden — recall@{K} ==="]
    for bucket in sorted(by_bucket):
        rows = by_bucket[bucket]
        passes = sum(1 for p, _, _, _ in rows if p)
        weighted_sum = sum(w for _, w, _, _ in rows)
        n = len(rows)
        mean_index_ms = sum(dt for _, _, dt, _ in rows) / n
        lines.append(
            f"  {bucket:<11} {passes:>2}/{n:<2}  ({passes / n:>5.1%})  "
            f"weighted {weighted_sum / n:>4.2f}  mean idx {mean_index_ms:5.2f} ms"
        )
    overall_pass = sum(1 for _, _, p, _, _, _ in results if p)
    overall_n = len(results)
    overall_rate = overall_pass / overall_n
    overall_weighted = sum(w for _, _, _, w, _, _ in results) / overall_n
    index_latencies = [dt for _, _, _, _, dt, _ in results]
    tool_latencies = [dt for _, _, _, _, _, dt in results]
    p95_index = _percentile(index_latencies, 95)
    p95_tool = _percentile(tool_latencies, 95)
    lines.append(
        f"  {'overall':<11} {overall_pass:>2}/{overall_n:<2}  ({overall_rate:>5.1%})  "
        f"weighted {overall_weighted:>4.2f}  "
        f"p95 idx {p95_index:5.2f} ms  p95 tool {p95_tool:5.2f} ms"
    )
    # Failed-case roll-up makes failure diagnostics one line away.
    failures = [cid for cid, _, p, _, _, _ in results if not p]
    if failures:
        lines.append("  failed: " + ", ".join(failures))
    print("\n".join(lines))

    bucket_violations: list[str] = []
    for bucket, floor in BUCKET_FLOORS.items():
        rows = by_bucket.get(bucket, [])
        if not rows:
            continue
        rate = sum(1 for p, _, _, _ in rows if p) / len(rows)
        if rate < floor:
            bucket_violations.append(f"{bucket} recall@{K}={rate:.1%} below floor {floor:.0%}")
    assert not bucket_violations, "; ".join(bucket_violations)
    assert p95_index < P95_LATENCY_MS, (
        f"index-only p95 latency={p95_index:.2f}ms exceeds {P95_LATENCY_MS}ms"
    )


async def test_search_convictions_empty_query_raises(ctx_for_real_corpus):
    with pytest.raises(EmptyQueryError):
        await search_convictions(ctx_for_real_corpus, query="", k=5)


async def test_search_convictions_whitespace_query_raises(ctx_for_real_corpus):
    with pytest.raises(EmptyQueryError):
        await search_convictions(ctx_for_real_corpus, query="   \t\n", k=5)


async def test_search_convictions_returns_passage_hits_with_metadata(ctx_for_real_corpus):
    hits = await search_convictions(ctx_for_real_corpus, query="CDB tributação", k=3)
    assert hits, "expected at least one hit on a basic PT query"
    h = hits[0]
    assert h.passage_id
    assert h.document_id
    assert h.document_title
    assert isinstance(h.heading_path, list) and h.heading_path
    assert h.snippet
    assert isinstance(h.score, float)
