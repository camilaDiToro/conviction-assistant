"""Tests for the combined deterministic + judge aggregator."""

import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import pytest

from evals.judge.aggregate import (
    _check_signature,
    _judge_aggregate,
    _judge_by_bucket,
    _judge_frame,
    _render,
    _worst_offenders,
)
from evals.judge.schema import (
    AnswerRelevancyScore,
    CitationAttributionScore,
    CompletenessScore,
    ConflictDisclosureScore,
    FaithfulnessScore,
    JudgeResult,
    RuleAPurityScore,
)


def _ok(
    qid: str,
    *,
    judge_model: str = "claude-opus-4-7",
    judge_prompt_hash: str = "abc12345",
    faithfulness: float = 1.0,
    n_sentences: int = 2,
    n_supported: int = 2,
    attribution: float = 1.0,
    n_markers: int = 2,
    n_correct: int = 2,
    rule_a_label: str = "clean",
    rule_a_leaked: list[str] | None = None,
) -> JudgeResult:
    rule_a_score = 1.0 if rule_a_label == "clean" else 0.0 if rule_a_label == "leaked" else None
    return JudgeResult(
        id=qid,
        judge_model=judge_model,
        judge_prompt_hash=judge_prompt_hash,
        judged_at=datetime(2026, 5, 11, 12, 0, tzinfo=UTC),
        faithfulness=FaithfulnessScore(
            score=faithfulness, n_sentences=n_sentences, n_supported=n_supported, reason="ok"
        ),
        answer_relevancy=AnswerRelevancyScore(label="relevant", score=1.0, reason="ok"),
        conflict_disclosure=ConflictDisclosureScore(
            applicable=False, label="n/a", score=None, reason="not rule_b"
        ),
        rule_a_purity=RuleAPurityScore(
            label=rule_a_label,  # type: ignore[arg-type]
            score=rule_a_score,
            leaked_sentences=rule_a_leaked or [],
            reason="ok",
        ),
        citation_attribution=CitationAttributionScore(
            score=attribution, n_markers=n_markers, n_correct=n_correct, reason="ok"
        ),
        completeness=CompletenessScore(label="complete", score=1.0, reason="ok"),
    )


# --- signature check -------------------------------------------------------


def test_check_signature_uniform_passes() -> None:
    sig = _check_signature([_ok("q01"), _ok("q02")])
    assert sig.judge_model == "claude-opus-4-7"


def test_check_signature_rejects_mixed_models() -> None:
    a = _ok("q01")
    b = _ok("q02", judge_model="gpt-5")
    with pytest.raises(ValueError, match="multiple"):
        _check_signature([a, b])


def test_check_signature_empty_raises() -> None:
    with pytest.raises(ValueError, match="empty"):
        _check_signature([])


# --- frame + aggregate -----------------------------------------------------


def test_judge_frame_includes_all_metrics() -> None:
    df = _judge_frame([_ok("q01"), _ok("q02")])
    assert set(df.columns) >= {
        "id",
        "faithfulness",
        "answer_relevancy",
        "conflict_disclosure",
        "rule_a_purity",
        "citation_attribution",
        "completeness",
    }


def test_judge_aggregate_excludes_nulls() -> None:
    df = _judge_frame([_ok("q01", faithfulness=0.5, n_supported=1), _ok("q02")])
    agg = _judge_aggregate(df)
    assert agg["faithfulness"] == 0.75
    # conflict_disclosure is None on both → aggregate is None.
    assert agg["conflict_disclosure"] is None


def test_judge_by_bucket_groups() -> None:
    judge_df = _judge_frame([_ok("q01"), _ok("q02")])
    det_df = pd.DataFrame(
        [
            {"id": "q01", "bucket": "factual"},
            {"id": "q02", "bucket": "rule_a"},
        ]
    )
    merged = pd.merge(det_df, judge_df, on="id")
    by_bucket = _judge_by_bucket(merged)
    assert set(by_bucket) == {"factual", "rule_a"}
    assert by_bucket["factual"]["faithfulness"] == 1.0


# --- worst offenders -------------------------------------------------------


def test_worst_offenders_flags_anchored_unfaithful() -> None:
    judge_df = _judge_frame(
        [
            _ok("q01", faithfulness=0.5, n_supported=1),  # anchored but unfaithful
            _ok("q02"),  # clean
        ]
    )
    det_df = pd.DataFrame(
        [
            {"id": "q01", "bucket": "factual", "anchor_rate": 1.0},
            {"id": "q02", "bucket": "factual", "anchor_rate": 1.0},
        ]
    )
    merged = pd.merge(det_df, judge_df, on="id")
    offenders = _worst_offenders(merged)
    assert len(offenders) == 1
    assert offenders[0]["id"] == "q01"
    assert "faithfulness" in str(offenders[0]["flagged"])


def test_worst_offenders_flags_rule_a_leaks() -> None:
    judge_df = _judge_frame([_ok("q01", rule_a_label="leaked", rule_a_leaked=["X."])])
    det_df = pd.DataFrame([{"id": "q01", "bucket": "rule_a", "anchor_rate": 1.0}])
    merged = pd.merge(det_df, judge_df, on="id")
    offenders = _worst_offenders(merged)
    assert len(offenders) == 1
    assert "rule_a_purity" in str(offenders[0]["flagged"])


def test_worst_offenders_empty_when_clean() -> None:
    judge_df = _judge_frame([_ok("q01")])
    det_df = pd.DataFrame([{"id": "q01", "bucket": "factual", "anchor_rate": 1.0}])
    merged = pd.merge(det_df, judge_df, on="id")
    assert _worst_offenders(merged) == []


# --- end-to-end render -----------------------------------------------------


def test_render_smoke(tmp_path: Path) -> None:
    judge_df = _judge_frame([_ok("q01")])
    det_df = pd.DataFrame(
        [
            {
                "id": "q01",
                "bucket": "factual",
                "anchor_rate": 1.0,
                "citation_precision": 1.0,
                "citation_recall": 1.0,
            }
        ]
    )
    merged = pd.merge(det_df, judge_df, on="id")
    body = _render(
        det_metadata={"timestamp": "2026-05-11", "model": "gpt-5"},
        judge_signature=_check_signature([_ok("q01")]),
        det_df=det_df,
        merged=merged,
        judge_agg=_judge_aggregate(judge_df),
        judge_by_bucket=_judge_by_bucket(merged),
        offenders=_worst_offenders(merged),
    )
    assert "Combined eval report" in body
    assert "judge_prompt_hash" in body
    assert "q01" in body


def test_main_cli_end_to_end(tmp_path: Path) -> None:
    """Drive the CLI via its module entrypoint to confirm pieces fit."""
    import subprocess
    import sys

    # Build minimal artefacts.
    det_csv = tmp_path / "det.csv"
    det_csv.write_text(
        "id,bucket,anchor_rate,citation_precision,citation_recall\nq01,factual,1.0,1.0,1.0\n",
        encoding="utf-8",
    )
    det_json = tmp_path / "det.json"
    det_json.write_text(
        json.dumps({"run_metadata": {"timestamp": "2026-05-11", "model": "gpt-5"}}),
        encoding="utf-8",
    )
    judge = tmp_path / "judge.jsonl"
    judge.write_text(_ok("q01").model_dump_json() + "\n", encoding="utf-8")
    out = tmp_path / "combined.md"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "evals.judge.aggregate",
            str(det_csv),
            str(judge),
            "--out",
            str(out),
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert completed.returncode == 0, completed.stderr
    assert out.exists()
    body = out.read_text(encoding="utf-8")
    assert "judge_prompt_hash" in body
