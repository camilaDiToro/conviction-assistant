"""Tests for the judge loader (trace → JudgeInput + judge JSONL round-trip)."""

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from evals.judge.loader import (
    JudgeInput,
    iter_judge_inputs,
    load_judge_results,
    prompt_hash,
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


def _trace_line(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "id": "q01",
        "bucket": "factual",
        "language": "en",
        "question": "What is a CDB?",
        "expected_passage_ids": ["cdbs#tax"],
        "expected_out_of_scope": False,
        "expected_general_knowledge": False,
        "expected_conflict_mention": False,
        "must_cite_at_least": 1,
        "duration_ms": 42,
        "result": {
            "output": {
                "kind": "answer",
                "answer": "A CDB is a Brazilian fixed-income product [1].",
                "citations": [{"passage_id": "cdbs#tax", "quote": "fixed-income product"}],
                "general_knowledge_used": False,
                "general_knowledge_section": None,
                "out_of_scope": False,
            },
            "rewritten_question": None,
            "language": "en",
            "steps": [],
            "tool_call_count": 0,
            "search_count": 0,
            "resolution": {
                "entries": [
                    {
                        "passage_id": "cdbs#tax",
                        "document_id": "cdbs",
                        "document_title": "CDBs",
                        "heading_path": ["CDBs", "Tax"],
                        "passage_text": "A CDB is a fixed-income product…",
                        "start": 0,
                        "end": 21,
                        "failure_reason": None,
                    }
                ]
            },
        },
    }
    base.update(overrides)
    return base


def test_iter_judge_inputs_happy(tmp_path: Path) -> None:
    traces = tmp_path / "traces.jsonl"
    traces.write_text(json.dumps(_trace_line()) + "\n", encoding="utf-8")
    inputs = list(iter_judge_inputs(traces))
    assert len(inputs) == 1
    inp = inputs[0]
    assert isinstance(inp, JudgeInput)
    assert inp.id == "q01"
    assert inp.must_cite_at_least == 1
    assert inp.output_kind == "answer"
    assert inp.answer is not None and "[1]" in inp.answer
    assert len(inp.citations) == 1
    cite = inp.citations[0]
    assert cite.marker == 1
    assert cite.anchored is True
    assert cite.passage_text.startswith("A CDB")


def test_iter_judge_inputs_skips_error_rows(tmp_path: Path) -> None:
    traces = tmp_path / "traces.jsonl"
    err = {
        "id": "qerr",
        "bucket": "factual",
        "language": "en",
        "question": "boom",
        "expected_passage_ids": [],
        "expected_out_of_scope": False,
        "expected_general_knowledge": False,
        "expected_conflict_mention": False,
        "must_cite_at_least": 1,
        "duration_ms": 0,
        "error": "kaboom",
        "result": None,
    }
    traces.write_text(
        json.dumps(err) + "\n" + json.dumps(_trace_line()) + "\n",
        encoding="utf-8",
    )
    inputs = list(iter_judge_inputs(traces))
    assert [i.id for i in inputs] == ["q01"]


def test_iter_judge_inputs_clarifying_turn(tmp_path: Path) -> None:
    raw = _trace_line()
    raw["result"]["output"] = {  # type: ignore[index]
        "kind": "clarifying_question",
        "question": "Do you mean LCI or LCA?",
        "options": ["LCI", "LCA"],
    }
    raw["result"]["resolution"] = None  # type: ignore[index]
    traces = tmp_path / "traces.jsonl"
    traces.write_text(json.dumps(raw) + "\n", encoding="utf-8")
    inp = next(iter_judge_inputs(traces))
    assert inp.output_kind == "clarifying_question"
    assert inp.answer is None
    assert inp.clarifying_question == "Do you mean LCI or LCA?"
    assert inp.citations == []


def test_load_judge_results_validates(tmp_path: Path) -> None:
    judge = tmp_path / "judge.jsonl"
    record = JudgeResult(
        id="q01",
        judge_model="claude-opus-4-7",
        judge_prompt_hash="abc12345",
        judged_at=datetime(2026, 5, 11, 12, 0, 0, tzinfo=UTC),
        faithfulness=FaithfulnessScore(score=1.0, n_sentences=1, n_supported=1, reason="ok"),
        answer_relevancy=AnswerRelevancyScore(label="relevant", score=1.0, reason="ok"),
        conflict_disclosure=ConflictDisclosureScore(
            applicable=False, label="n/a", score=None, reason="not rule_b"
        ),
        rule_a_purity=RuleAPurityScore(label="clean", score=1.0, reason="ok"),
        citation_attribution=CitationAttributionScore(
            score=1.0, n_markers=1, n_correct=1, reason="ok"
        ),
        completeness=CompletenessScore(label="complete", score=1.0, reason="ok"),
    )
    judge.write_text(record.model_dump_json() + "\n", encoding="utf-8")
    loaded = load_judge_results(judge)
    assert len(loaded) == 1
    assert loaded[0].id == "q01"


def test_load_judge_results_rejects_invalid(tmp_path: Path) -> None:
    judge = tmp_path / "judge.jsonl"
    # label/score mismatch — should fail validation.
    judge.write_text('{"id": "q01", "judge_model": "x"}\n', encoding="utf-8")
    with pytest.raises(ValueError, match="invalid judge record"):
        load_judge_results(judge)


def test_prompt_hash_stable(tmp_path: Path) -> None:
    p = tmp_path / "prompt.md"
    p.write_text("hello world", encoding="utf-8")
    h1 = prompt_hash(p)
    h2 = prompt_hash(p)
    assert h1 == h2
    assert len(h1) == 8
