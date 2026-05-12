"""Smoke test for the eval runner.

Marked ``@pytest.mark.eval`` so it stays out of the default CI run.
Skipped unless ``OPENAI_API_KEY`` is set. The runner uses real provider
tokens; this only runs 3 questions to confirm the pipeline
end-to-end doesn't crash.

Run with:

    uv run pytest -m eval

Do NOT add this to default CI — it burns tokens.
"""

import os
from pathlib import Path

import pandas as pd
import pytest

from evals.dataset import Golden
from evals.report import RunMetadata, write_run
from evals.run import _row_from_result, _trace_record

EVALS_RESULTS_DIR = Path(__file__).resolve().parents[2] / "evals" / "results"


def test_row_from_result_with_synthetic_data(tmp_path: Path) -> None:
    """Pure unit test of the row builder — no LLM, no API. Verifies
    the runner correctly threads agent output + resolver entries
    through to the four custom metrics."""
    from app.agent.resolver import CitationResolution, OffsetResolution
    from app.agent.schemas import AgentResult, AnswerOutput, Citation

    output = AnswerOutput(
        kind="answer",
        answer="The answer is X.",
        citations=[Citation(passage_id="cdbs#tax", quote="some text")],
        general_knowledge_used=False,
        general_knowledge_section=None,
        out_of_scope=False,
    )
    resolution = OffsetResolution(
        entries=[
            CitationResolution(
                passage_id="cdbs#tax",
                document_id="cdbs",
                document_title="CDBs",
                heading_path=["CDBs", "tax"],
                passage_text="some text full",
                start=0,
                end=9,
                failure_reason=None,
            )
        ]
    )
    result = AgentResult(
        output=output,
        rewritten_question=None,
        language="en",
        steps=[],
        tool_call_count=1,
        search_count=1,
        resolution=resolution,
    )
    golden = Golden(
        id="qsmoke",
        question="What is a CDB?",
        language="en",
        bucket="factual",
        expected_passage_ids=("cdbs#tax",),
    )
    row = _row_from_result(golden, result, duration_ms=42)
    assert row.id == "qsmoke"
    assert row.anchor_rate == 1.0
    assert row.citation_precision == 1.0
    assert row.citation_recall == 1.0
    # refusal_correctness is now widened: in-scope question that did not refuse → correct.
    assert row.refusal_correctness == "correct"
    assert row.general_knowledge_correctness == "correct"
    assert row.clarify_correctness == "n/a"
    assert row.meets_min_citations == "correct"
    assert row.conflict_min_citations == "n/a"
    assert row.conflict_disclosure_det == "n/a"
    assert row.language_match == "correct"
    assert row.duration_ms == 42

    # Make sure write_run can serialize one synthetic row through the
    # full reporting pipeline (CSV/JSON/MD) without crashing.
    df = pd.DataFrame([row.as_dict()])
    metadata = RunMetadata(
        timestamp="2026-05-11_00-00-00",
        provider="openai",
        model="stub",
        reasoning_effort="low",
        rewrite_reasoning_effort="minimal",
        agent_max_tool_calls=5,
        agent_max_output_tokens=8192,
        git_sha=None,
        subset="smoke",
        with_judge=False,
    )
    csv, jsn, md = write_run(df=df, metadata=metadata, out_dir=tmp_path, stem="smoke")
    assert csv.exists() and jsn.exists() and md.exists()
    body = md.read_text(encoding="utf-8")
    assert "qsmoke" in body
    assert "anchor rate" in body.lower()

    # Trace record serialises the full AgentResult — output + steps + resolution.
    import json as _json

    trace = _trace_record(golden, result, duration_ms=42)
    assert trace["id"] == "qsmoke"
    assert trace["result"]["output"]["kind"] == "answer"
    assert trace["result"]["resolution"]["entries"][0]["passage_id"] == "cdbs#tax"
    # Must round-trip through JSON (datetime + nested models serialise cleanly).
    line = _json.dumps(trace, ensure_ascii=False)
    assert _json.loads(line)["id"] == "qsmoke"

    # Error-path trace skips the result block.
    err_trace = _trace_record(golden, None, 0, error="boom")
    assert err_trace["error"] == "boom"
    assert err_trace["result"] is None


@pytest.mark.eval
@pytest.mark.skipif(
    not os.environ.get("OPENAI_API_KEY"),
    reason="OPENAI_API_KEY not set; eval runner needs a real provider",
)
def test_runner_smoke_three_questions(tmp_path: Path) -> None:
    """Hits real OpenAI. Only runs when explicitly requested via
    ``pytest -m eval``. Caps to 3 questions to keep token usage bounded."""
    import subprocess
    import sys

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "evals.run",
            "--provider",
            "openai",
            "--reasoning",
            "low",
            "--limit",
            "3",
            "--out",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert completed.returncode == 0, completed.stderr
    csvs = list(tmp_path.glob("*.csv"))
    assert csvs, "runner produced no CSV"
    mds = list(tmp_path.glob("*.md"))
    assert mds, "runner produced no Markdown report"
