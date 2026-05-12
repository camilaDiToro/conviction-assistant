"""Unit tests for the deterministic eval metrics.

These run without an LLM — they exercise the metric logic against
synthetic citation lists and structured-output dicts. No tokens burnt.
"""

from evals.metrics import (
    anchor_rate,
    citation_precision,
    general_knowledge_correctness,
    refusal_correctness,
)


def test_anchor_rate_all_anchored() -> None:
    citations = [
        {"passage_id": "p1", "failure_reason": None},
        {"passage_id": "p2", "failure_reason": None},
    ]
    r = anchor_rate.score(citations=citations)
    assert float(r) == 1.0
    assert "2/2" in (r.reason or "")


def test_anchor_rate_partial() -> None:
    citations = [
        {"passage_id": "p1", "failure_reason": None},
        {"passage_id": "p2", "failure_reason": "offset_not_found"},
        {"passage_id": "p3", "failure_reason": None},
    ]
    r = anchor_rate.score(citations=citations)
    assert abs(float(r) - (2 / 3)) < 1e-9


def test_anchor_rate_no_citations() -> None:
    r = anchor_rate.score(citations=[])
    assert float(r) == 0.0
    assert "no citations" in (r.reason or "").lower()


def test_citation_precision_perfect() -> None:
    citations = [
        {"passage_id": "p1", "failure_reason": None},
        {"passage_id": "p2", "failure_reason": None},
    ]
    r = citation_precision.score(citations=citations, expected_passage_ids=["p1", "p2", "p3"])
    assert float(r) == 1.0


def test_citation_precision_one_wrong() -> None:
    citations = [
        {"passage_id": "p1", "failure_reason": None},
        {"passage_id": "p99", "failure_reason": None},
    ]
    r = citation_precision.score(citations=citations, expected_passage_ids=["p1", "p2"])
    assert float(r) == 0.5


def test_citation_precision_not_applicable() -> None:
    r = citation_precision.score(citations=[{"passage_id": "p1"}], expected_passage_ids=[])
    # When the golden has no expected ids, precision is "not applicable" → 1.0.
    assert float(r) == 1.0
    assert "not applicable" in (r.reason or "").lower()


def test_refusal_correctness_correct_refusal() -> None:
    output = {"kind": "answer", "out_of_scope": True}
    r = refusal_correctness.score(output=output, expected_out_of_scope=True)
    assert r.value == "correct"


def test_refusal_correctness_missed_refusal() -> None:
    output = {"kind": "answer", "out_of_scope": False}
    r = refusal_correctness.score(output=output, expected_out_of_scope=True)
    assert r.value == "incorrect"


def test_refusal_correctness_clarify_when_expected_refusal() -> None:
    output = {"kind": "clarifying_question", "question": "huh?"}
    r = refusal_correctness.score(output=output, expected_out_of_scope=True)
    assert r.value == "incorrect"


def test_refusal_correctness_not_applicable() -> None:
    output = {"kind": "answer", "out_of_scope": False}
    r = refusal_correctness.score(output=output, expected_out_of_scope=False)
    assert r.value == "n/a"


def test_general_knowledge_correctness_true_positive() -> None:
    output = {
        "kind": "answer",
        "out_of_scope": False,
        "general_knowledge_used": True,
        "general_knowledge_section": "extra...",
    }
    r = general_knowledge_correctness.score(output=output, expected_general_knowledge=True)
    assert r.value == "correct"


def test_general_knowledge_correctness_false_positive() -> None:
    output = {
        "kind": "answer",
        "out_of_scope": False,
        "general_knowledge_used": True,
        "general_knowledge_section": "leaked",
    }
    r = general_knowledge_correctness.score(output=output, expected_general_knowledge=False)
    assert r.value == "incorrect"


def test_general_knowledge_correctness_not_applicable_for_clarify() -> None:
    output = {"kind": "clarifying_question"}
    r = general_knowledge_correctness.score(output=output, expected_general_knowledge=False)
    assert r.value == "n/a"


def test_general_knowledge_correctness_not_applicable_for_out_of_scope() -> None:
    output = {"kind": "answer", "out_of_scope": True, "general_knowledge_used": False}
    r = general_knowledge_correctness.score(output=output, expected_general_knowledge=False)
    assert r.value == "n/a"
