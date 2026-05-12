"""Unit tests for the deterministic eval metrics.

These run without an LLM — they exercise the metric logic against
synthetic citation lists and structured-output dicts. No tokens burnt.
"""

from evals.metrics import (
    _detect_language,
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


def test_citation_precision_perfect_with_extras_not_penalised() -> None:
    # All expected are cited; one extra outside the expected set must not
    # lower the score (extras are treated as neutral).
    citations = [
        {"passage_id": "p1", "failure_reason": None},
        {"passage_id": "p2", "failure_reason": None},
        {"passage_id": "p99", "failure_reason": None},
    ]
    r = citation_precision.score(citations=citations, expected_passage_ids=["p1", "p2"])
    assert float(r) == 1.0
    assert "not penalised" in (r.reason or "")


def test_citation_precision_subset_of_expected() -> None:
    # Agent cited 2 of 3 expected ids with no extras → 2/3.
    citations = [
        {"passage_id": "p1", "failure_reason": None},
        {"passage_id": "p2", "failure_reason": None},
    ]
    r = citation_precision.score(citations=citations, expected_passage_ids=["p1", "p2", "p3"])
    assert abs(float(r) - (2 / 3)) < 1e-9


def test_citation_precision_missing_one_expected_with_extra() -> None:
    # Agent missed one expected id but added an unrelated cite; the missing
    # one drops the score, the extra does not.
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


def test_refusal_correctness_correct_no_refusal() -> None:
    # In-scope question, agent did not refuse → correct (widened metric).
    output = {"kind": "answer", "out_of_scope": False}
    r = refusal_correctness.score(output=output, expected_out_of_scope=False)
    assert r.value == "correct"


def test_refusal_correctness_false_refusal() -> None:
    # In-scope question, agent refused → incorrect (widened metric).
    output = {"kind": "answer", "out_of_scope": True}
    r = refusal_correctness.score(output=output, expected_out_of_scope=False)
    assert r.value == "incorrect"
    assert "false refusal" in (r.reason or "").lower()


def test_refusal_correctness_clarifying_question_on_in_scope_defers() -> None:
    # Clarifying-question outputs are scored by clarify_correctness, not refusal.
    output = {"kind": "clarifying_question", "question": "?"}
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


# --- citation_recall -------------------------------------------------------


def test_citation_recall_perfect() -> None:
    citations = [
        {"passage_id": "p1", "failure_reason": None},
        {"passage_id": "p2", "failure_reason": None},
    ]
    r = citation_recall.score(citations=citations, expected_passage_ids=["p1", "p2"])
    assert float(r) == 1.0


def test_citation_recall_one_missing() -> None:
    citations = [{"passage_id": "p1", "failure_reason": None}]
    r = citation_recall.score(citations=citations, expected_passage_ids=["p1", "p2"])
    assert float(r) == 0.5


def test_citation_recall_not_applicable() -> None:
    r = citation_recall.score(citations=[], expected_passage_ids=[])
    assert float(r) == 1.0
    assert "not applicable" in (r.reason or "").lower()


def test_citation_recall_no_citations() -> None:
    r = citation_recall.score(citations=[], expected_passage_ids=["p1"])
    assert float(r) == 0.0


# --- clarify_correctness ---------------------------------------------------


def test_clarify_correctness_correct_on_clarify_bucket() -> None:
    output = {"kind": "clarifying_question", "question": "?"}
    r = clarify_correctness.score(output=output, bucket="clarify")
    assert r.value == "correct"


def test_clarify_correctness_missing_clarify() -> None:
    output = {"kind": "answer", "out_of_scope": False}
    r = clarify_correctness.score(output=output, bucket="clarify")
    assert r.value == "incorrect"


def test_clarify_correctness_wrongful_clarify_on_factual() -> None:
    output = {"kind": "clarifying_question", "question": "?"}
    r = clarify_correctness.score(output=output, bucket="factual")
    assert r.value == "incorrect"
    assert "wrongful" in (r.reason or "").lower()


def test_clarify_correctness_not_applicable_for_factual_answer() -> None:
    output = {"kind": "answer", "out_of_scope": False}
    r = clarify_correctness.score(output=output, bucket="factual")
    assert r.value == "n/a"


# --- meets_min_citations ---------------------------------------------------


def test_meets_min_citations_correct() -> None:
    citations = [
        {"passage_id": "p1", "failure_reason": None},
        {"passage_id": "p2", "failure_reason": None},
    ]
    r = meets_min_citations.score(citations=citations, must_cite_at_least=2)
    assert r.value == "correct"


def test_meets_min_citations_counts_distinct() -> None:
    # Two citations against the same passage do not satisfy a min of 2.
    citations = [
        {"passage_id": "p1", "failure_reason": None},
        {"passage_id": "p1", "failure_reason": None},
    ]
    r = meets_min_citations.score(citations=citations, must_cite_at_least=2)
    assert r.value == "incorrect"


def test_meets_min_citations_not_applicable_for_zero() -> None:
    r = meets_min_citations.score(citations=[], must_cite_at_least=0)
    assert r.value == "n/a"


# --- conflict_min_citations ------------------------------------------------


def test_conflict_min_citations_correct() -> None:
    citations = [
        {"passage_id": "side_a", "failure_reason": None},
        {"passage_id": "side_b", "failure_reason": None},
    ]
    r = conflict_min_citations.score(citations=citations, expected_conflict_mention=True)
    assert r.value == "correct"


def test_conflict_min_citations_single_side_fails() -> None:
    citations = [{"passage_id": "side_a", "failure_reason": None}]
    r = conflict_min_citations.score(citations=citations, expected_conflict_mention=True)
    assert r.value == "incorrect"


def test_conflict_min_citations_not_applicable() -> None:
    r = conflict_min_citations.score(citations=[], expected_conflict_mention=False)
    assert r.value == "n/a"


# --- language_match --------------------------------------------------------


def test_language_match_es_correct() -> None:
    output = {
        "kind": "answer",
        "answer": "Los CDB se gravan según una tabla regresiva del impuesto sobre la renta.",
    }
    r = language_match.score(output=output, expected_language="es")
    assert r.value == "correct"


def test_language_match_pt_correct() -> None:
    output = {
        "kind": "answer",
        "answer": "Os CDBs são tributados segundo uma tabela regressiva do imposto de renda.",
    }
    r = language_match.score(output=output, expected_language="pt")
    assert r.value == "correct"


def test_language_match_en_correct() -> None:
    output = {
        "kind": "answer",
        "answer": (
            "CDBs are taxed under a regressive income-tax table that depends on holding period."
        ),
    }
    r = language_match.score(output=output, expected_language="en")
    assert r.value == "correct"


def test_language_match_mismatch_flagged() -> None:
    output = {
        "kind": "answer",
        "answer": "The answer is in English even though the user asked in Spanish.",
    }
    r = language_match.score(output=output, expected_language="es")
    assert r.value == "incorrect"


def test_language_match_uses_clarifying_question_text() -> None:
    output = {"kind": "clarifying_question", "question": "¿Sobre qué tema querés consultarme?"}
    r = language_match.score(output=output, expected_language="es")
    assert r.value == "correct"


def test_language_match_n_a_on_empty_text() -> None:
    output = {"kind": "answer", "answer": ""}
    r = language_match.score(output=output, expected_language="es")
    assert r.value == "n/a"


# --- _detect_language helper ----------------------------------------------


def test_detect_language_pt_diacritics_strong_signal() -> None:
    # Even a short PT-only string with ã/ç should be detected as PT.
    assert _detect_language("ação não está disponível") == "pt"


def test_detect_language_es_diacritics_strong_signal() -> None:
    assert _detect_language("¿qué pasó con la información?") == "es"


def test_detect_language_en_baseline() -> None:
    assert _detect_language("the agent answers in english") == "en"
