"""Eval runner CLI.

Usage:

    uv run python -m evals.run --reasoning low --limit 5
    uv run python -m evals.run --bucket rule_b
    uv run python -m evals.run --id q07
    uv run python -m evals.run                            # full set

Loads ``evals/golden_set.yaml``, runs each entry end-to-end through
``app.agent.run`` against a real LLM provider (OpenAI by default), runs
our four deterministic metrics, writes CSV/JSON/MD to
``evals/results/``.

Real OpenAI calls use provider quota. Smoke runs with ``--limit`` first.
"""

import argparse
import asyncio
import hashlib
import json
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import Any

import pandas as pd

from app.agent import run as run_agent
from app.agent.schemas import (
    AgentResult,
    AnswerOutput,
    ClarifyingQuestionOutput,
    ConversationTurn,
)
from app.agent.tools import ToolContext
from app.config import db, settings
from app.providers import get_llm_provider
from app.providers.base import LLMProvider
from app.retrieval import get_retriever
from evals.dataset import Golden, GoldenSet, load_golden_set
from evals.metrics import (
    anchor_rate,
    citation_precision,
    citation_recall,
    clarify_correctness,
    conflict_min_citations,
    general_knowledge_correctness,
    language_match,
    meets_min_citations,
    refusal_correctness,
)
from evals.report import RunMetadata, iter_required_columns, write_run

GOLDEN_PATH = Path(__file__).resolve().parent / "golden_set.yaml"
DEFAULT_OUT_DIR = Path(__file__).resolve().parent / "results"
_SYSTEM_PROMPT_PATH = (
    Path(__file__).resolve().parents[1] / "app" / "agent" / "prompts" / "system.md"
)


def _prompt_version() -> str:
    """Short content hash of the system prompt, so a report stamps the
    exact prompt revision that produced its numbers — crucial when
    comparing runs across a prompt rewrite."""
    try:
        body = _SYSTEM_PROMPT_PATH.read_bytes()
    except OSError:
        return "unknown"
    return hashlib.sha256(body).hexdigest()[:8]


# ---- per-question record -------------------------------------------------


@dataclass
class _QuestionRow:
    id: str
    bucket: str
    language: str
    question: str
    expected_passage_ids_count: int
    citations_count: int
    anchored_count: int
    anchor_rate: float
    anchor_rate_reason: str
    citation_precision: float
    citation_precision_reason: str
    citation_recall: float
    citation_recall_reason: str
    refusal_correctness: str
    refusal_correctness_reason: str
    general_knowledge_correctness: str
    general_knowledge_correctness_reason: str
    clarify_correctness: str
    clarify_correctness_reason: str
    meets_min_citations: str
    meets_min_citations_reason: str
    conflict_min_citations: str
    conflict_min_citations_reason: str
    language_match: str
    language_match_reason: str
    prompt_tokens: int
    completion_tokens: int
    cached_tokens: int
    reasoning_tokens: int
    tool_calls: int
    duration_ms: int
    output_kind: str
    output_summary: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---- runner ---------------------------------------------------------------


async def _run_question(
    golden: Golden, *, llm: LLMProvider, factory: Any, retriever: Any
) -> tuple[_QuestionRow, AgentResult, int]:
    history = [
        ConversationTurn(role=role, content=content)  # type: ignore[arg-type]
        for role, content in golden.prior_turns
    ]
    async with factory() as session:
        tool_ctx = ToolContext(session=session, retriever=retriever)
        t0 = perf_counter()
        result = await run_agent(golden.question, history, tool_ctx=tool_ctx, llm=llm)
        duration_ms = int((perf_counter() - t0) * 1000)
    return _row_from_result(golden, result, duration_ms=duration_ms), result, duration_ms


def _trace_record(
    golden: Golden,
    result: AgentResult | None,
    duration_ms: int,
    *,
    error: str | None = None,
) -> dict[str, Any]:
    """One JSON-serialisable trace record per question.

    Carries the full ``AgentResult`` (steps, resolution entries, output)
    so a reviewer can debug why a specific question failed without
    re-running it.
    """
    trace: dict[str, Any] = {
        "id": golden.id,
        "bucket": golden.bucket,
        "language": golden.language,
        "question": golden.question,
        "prior_turns": [{"role": r, "content": c} for r, c in golden.prior_turns],
        "expected_passage_ids": list(golden.expected_passage_ids),
        "expected_out_of_scope": golden.expected_out_of_scope,
        "expected_general_knowledge": golden.expected_general_knowledge,
        "expected_conflict_mention": golden.expected_conflict_mention,
        "must_cite_at_least": golden.must_cite_at_least,
        "duration_ms": duration_ms,
    }
    if error is not None:
        trace["error"] = error
        trace["result"] = None
        return trace
    assert result is not None
    # Pydantic model_dump handles datetime / nested models cleanly.
    trace["result"] = result.model_dump(mode="json")
    return trace


def _row_from_result(golden: Golden, result: AgentResult, *, duration_ms: int) -> _QuestionRow:
    citations: list[dict[str, Any]] = []
    if result.resolution is not None:
        citations = [
            {
                "passage_id": e.passage_id,
                "failure_reason": e.failure_reason,
            }
            for e in result.resolution.entries
        ]
    citations_count = len(citations)
    anchored_count = sum(1 for c in citations if c["failure_reason"] is None)

    output_dict = _output_to_dict(result.output)

    token_usage = _sum_token_usage(result)
    tool_calls = sum(1 for s in result.steps if s.kind == "tool_call")

    expected_ids = list(golden.expected_passage_ids)
    anchor = anchor_rate.score(citations=citations)
    precision = citation_precision.score(citations=citations, expected_passage_ids=expected_ids)
    recall = citation_recall.score(citations=citations, expected_passage_ids=expected_ids)
    refusal = refusal_correctness.score(
        output=output_dict, expected_out_of_scope=golden.expected_out_of_scope
    )
    gen_know = general_knowledge_correctness.score(
        output=output_dict, expected_general_knowledge=golden.expected_general_knowledge
    )
    clarify = clarify_correctness.score(output=output_dict, bucket=golden.bucket)
    min_cite = meets_min_citations.score(
        citations=citations, must_cite_at_least=golden.must_cite_at_least
    )
    conflict = conflict_min_citations.score(
        citations=citations, expected_conflict_mention=golden.expected_conflict_mention
    )
    lang_match = language_match.score(output=output_dict, expected_language=golden.language)

    return _QuestionRow(
        id=golden.id,
        bucket=golden.bucket,
        language=golden.language,
        question=golden.question,
        expected_passage_ids_count=len(golden.expected_passage_ids),
        citations_count=citations_count,
        anchored_count=anchored_count,
        anchor_rate=float(anchor),
        anchor_rate_reason=anchor.reason or "",
        citation_precision=float(precision),
        citation_precision_reason=precision.reason or "",
        citation_recall=float(recall),
        citation_recall_reason=recall.reason or "",
        refusal_correctness=str(refusal.value),
        refusal_correctness_reason=refusal.reason or "",
        general_knowledge_correctness=str(gen_know.value),
        general_knowledge_correctness_reason=gen_know.reason or "",
        clarify_correctness=str(clarify.value),
        clarify_correctness_reason=clarify.reason or "",
        meets_min_citations=str(min_cite.value),
        meets_min_citations_reason=min_cite.reason or "",
        conflict_min_citations=str(conflict.value),
        conflict_min_citations_reason=conflict.reason or "",
        language_match=str(lang_match.value),
        language_match_reason=lang_match.reason or "",
        prompt_tokens=token_usage["prompt_tokens"],
        completion_tokens=token_usage["completion_tokens"],
        cached_tokens=token_usage["cached_tokens"],
        reasoning_tokens=token_usage["reasoning_tokens"],
        tool_calls=tool_calls,
        duration_ms=duration_ms,
        output_kind=str(output_dict.get("kind", "")),
        output_summary=_summarize_output(output_dict),
    )


def _sum_token_usage(result: AgentResult) -> dict[str, int]:
    totals = {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "cached_tokens": 0,
        "reasoning_tokens": 0,
    }
    for step in result.steps:
        if step.usage is None:
            continue
        totals["prompt_tokens"] += step.usage.prompt_tokens
        totals["completion_tokens"] += step.usage.completion_tokens
        totals["cached_tokens"] += step.usage.cached_tokens
        totals["reasoning_tokens"] += step.usage.reasoning_tokens
    return totals


def _output_to_dict(output: AnswerOutput | ClarifyingQuestionOutput) -> dict[str, Any]:
    return output.model_dump()


def _summarize_output(output: dict[str, Any]) -> str:
    if output.get("kind") == "clarifying_question":
        q = str(output.get("question", ""))
        return q[:160]
    answer = str(output.get("answer") or "")
    flags = []
    if output.get("out_of_scope"):
        flags.append("out_of_scope")
    if output.get("general_knowledge_used"):
        flags.append("gen_knowledge")
    flag_str = f" [{','.join(flags)}]" if flags else ""
    return (answer[:160] + flag_str).strip()


# ---- CLI -----------------------------------------------------------------


def _select(goldens: GoldenSet, args: argparse.Namespace) -> tuple[GoldenSet, str]:
    """Apply --id / --bucket / --limit to the golden set."""
    subset = "full"
    if args.id:
        goldens = goldens.by_id(args.id)
        if len(goldens) == 0:
            raise SystemExit(f"no golden entry with id {args.id!r}")
        subset = f"id-{args.id}"
    if args.bucket:
        goldens = goldens.by_bucket(args.bucket)
        if len(goldens) == 0:
            raise SystemExit(f"no golden entries with bucket {args.bucket!r}")
        subset = f"bucket-{args.bucket}" if subset == "full" else f"{subset}-bucket-{args.bucket}"
    if args.limit and args.limit < len(goldens):
        goldens = goldens.balanced_sample(args.limit)
        subset = f"limit{args.limit}" if subset == "full" else f"{subset}-limit{args.limit}"
    return goldens, subset


def _git_sha() -> str | None:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            timeout=2,
        )
        return out.stdout.strip() or None
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        return None


async def _amain(args: argparse.Namespace) -> int:
    goldens = load_golden_set(GOLDEN_PATH)
    goldens, subset = _select(goldens, args)
    print(f"Loaded {len(goldens)} golden entries (subset={subset})", file=sys.stderr)

    if args.dry_run:
        for g in goldens:
            print(f"  {g.id:<6} [{g.bucket:<13}] {g.language}  {g.question[:80]}")
        return 0

    # The LLM provider is the only thing the runner reaches for that needs
    # real OpenAI access. Settings.openai_api_key is required.
    if not settings.openai_api_key:
        raise SystemExit("OPENAI_API_KEY must be set (in .env or env) to run the eval")

    # Apply loop tuning for the whole run by patching settings BEFORE
    # building the LLM provider — the openai client
    # locks in the timeout at construction time.
    if args.reasoning:
        settings.agent_reasoning_effort = args.reasoning  # type: ignore[assignment]
    if args.rewrite_reasoning:
        settings.rewrite_reasoning_effort = args.rewrite_reasoning  # type: ignore[assignment]
    if args.timeout is not None:
        settings.openai_timeout_seconds = float(args.timeout)
    if args.model:
        settings.openai_model = args.model

    llm = get_llm_provider()
    settings_model = settings.openai_model

    db.migrate(settings.sqlite_path)
    engine = db.make_engine(settings.async_database_url)
    factory = db.make_session_factory(engine)
    retriever = get_retriever(settings.retrieval_strategy)
    async with factory() as session:
        await retriever.build(session)

    rows: list[_QuestionRow] = []
    traces: list[dict[str, Any]] = []
    try:
        for i, golden in enumerate(goldens, start=1):
            print(f"[{i}/{len(goldens)}] {golden.id} ({golden.bucket})", file=sys.stderr)
            try:
                row, result, q_duration = await _run_question(
                    golden, llm=llm, factory=factory, retriever=retriever
                )
                traces.append(_trace_record(golden, result, q_duration))
            except Exception as exc:  # noqa: BLE001
                # One bad question shouldn't kill the run — record a sentinel
                # row so the CSV stays aligned with the golden set.
                print(f"  ! error: {exc}", file=sys.stderr)
                row = _error_row(golden, str(exc))
                traces.append(_trace_record(golden, None, 0, error=str(exc)))
            rows.append(row)
    finally:
        await engine.dispose()

    df = pd.DataFrame([r.as_dict() for r in rows])
    # Make sure every column the report expects exists, even when the run
    # was empty or every question errored.
    for col in iter_required_columns():
        if col not in df.columns:
            df[col] = pd.NA

    timestamp = datetime.now(UTC).strftime("%Y-%m-%d_%H-%M-%S")
    stem = (
        f"{timestamp}_openai_{settings_model}_{settings.agent_reasoning_effort}"
        f"{'_' + subset if subset != 'full' else ''}"
    )
    metadata = RunMetadata(
        timestamp=timestamp,
        provider="openai",
        model=settings_model,
        reasoning_effort=settings.agent_reasoning_effort,
        rewrite_reasoning_effort=settings.rewrite_reasoning_effort,
        agent_max_tool_calls=settings.agent_max_tool_calls,
        agent_max_output_tokens=settings.agent_max_output_tokens,
        git_sha=_git_sha(),
        subset=subset,
        with_judge=False,
        prompt_version=_prompt_version(),
        openai_timeout_seconds=int(settings.openai_timeout_seconds),
    )
    csv_path, json_path, md_path = write_run(
        df=df, metadata=metadata, out_dir=Path(args.out), stem=stem
    )
    traces_path = Path(args.out) / f"{stem}_traces.jsonl"
    with traces_path.open("w", encoding="utf-8") as fh:
        for trace in traces:
            fh.write(json.dumps(trace, ensure_ascii=False) + "\n")
    print("Wrote:", file=sys.stderr)
    print(f"  {csv_path}", file=sys.stderr)
    print(f"  {json_path}", file=sys.stderr)
    print(f"  {md_path}", file=sys.stderr)
    print(f"  {traces_path}", file=sys.stderr)

    # Print aggregate as JSON to stdout so wrappers (CI, future scripts) can pipe it.
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    print(json.dumps(payload["aggregate"], indent=2))
    return 0


def _error_row(golden: Golden, msg: str) -> _QuestionRow:
    return _QuestionRow(
        id=golden.id,
        bucket=golden.bucket,
        language=golden.language,
        question=golden.question,
        expected_passage_ids_count=len(golden.expected_passage_ids),
        citations_count=0,
        anchored_count=0,
        anchor_rate=0.0,
        anchor_rate_reason=f"error: {msg[:120]}",
        citation_precision=0.0,
        citation_precision_reason="error",
        citation_recall=0.0,
        citation_recall_reason="error",
        refusal_correctness="n/a",
        refusal_correctness_reason="error",
        general_knowledge_correctness="n/a",
        general_knowledge_correctness_reason="error",
        clarify_correctness="n/a",
        clarify_correctness_reason="error",
        meets_min_citations="n/a",
        meets_min_citations_reason="error",
        conflict_min_citations="n/a",
        conflict_min_citations_reason="error",
        language_match="n/a",
        language_match_reason="error",
        prompt_tokens=0,
        completion_tokens=0,
        cached_tokens=0,
        reasoning_tokens=0,
        tool_calls=0,
        duration_ms=0,
        output_kind="error",
        output_summary=msg[:160],
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the eval suite (OpenAI only).")
    parser.add_argument("--provider", default="openai", choices=["openai"])
    parser.add_argument(
        "--model",
        default=None,
        help=(
            "override OPENAI_MODEL for this run (e.g. gpt-5.5, gpt-5.5-mini, "
            "gpt-5.4-mini, gpt-5-mini, o4-mini). Allowlist enforced by the "
            "provider factory; unsupported values raise at startup."
        ),
    )
    parser.add_argument(
        "--reasoning",
        default=None,
        choices=["none", "minimal", "low", "medium", "high", "xhigh"],
        help="set agent_reasoning_effort for this eval run",
    )
    parser.add_argument(
        "--rewrite-reasoning",
        default=None,
        choices=["none", "minimal", "low", "medium", "high", "xhigh"],
        help="set rewrite_reasoning_effort for this eval run",
    )
    parser.add_argument(
        "--limit", type=int, default=None, help="run a balanced sample of N questions"
    )
    parser.add_argument(
        "--bucket",
        default=None,
        choices=["factual", "rule_a", "rule_b", "cross_lang", "out_of_scope", "clarify"],
    )
    parser.add_argument("--id", default=None, help="single golden id (e.g. q07)")
    parser.add_argument(
        "--timeout",
        type=int,
        default=None,
        help="set openai client timeout in seconds (default 60). "
        "Raise to 180-240 for medium/high reasoning to avoid mid-call timeouts.",
    )
    parser.add_argument("--out", default=str(DEFAULT_OUT_DIR), help="output dir for csv/json/md")
    parser.add_argument("--dry-run", action="store_true", help="print selected golden ids and exit")
    args = parser.parse_args()
    return asyncio.run(_amain(args))


if __name__ == "__main__":
    raise SystemExit(main())
