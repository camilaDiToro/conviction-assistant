"""Tests for the LLM-as-judge schema.

Exercise every label↔score invariant, every numeric bound, and one
round-trip of JudgeResult through JSON.
"""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from evals.judge.schema import (
    METRIC_NAMES,
    AnswerRelevancyScore,
    CitationAttributionScore,
    CompletenessScore,
    ConflictDisclosureScore,
    FaithfulnessScore,
    JudgeResult,
    RuleAPurityScore,
)

# --- FaithfulnessScore -----------------------------------------------------


def test_faithfulness_happy_path() -> None:
    s = FaithfulnessScore(
        score=0.5, n_sentences=4, n_supported=2, unsupported=["X.", "Y."], reason="ok"
    )
    assert s.score == 0.5
    assert s.n_supported <= s.n_sentences


def test_faithfulness_rejects_inconsistent_counts() -> None:
    with pytest.raises(ValidationError):
        FaithfulnessScore(score=1.0, n_sentences=2, n_supported=3, reason="bad counts")


def test_faithfulness_rejects_score_out_of_range() -> None:
    with pytest.raises(ValidationError):
        FaithfulnessScore(score=1.5, n_sentences=0, n_supported=0, reason="bad")


def test_faithfulness_caps_unsupported_list() -> None:
    with pytest.raises(ValidationError):
        FaithfulnessScore(
            score=0.0,
            n_sentences=6,
            n_supported=0,
            unsupported=["a", "b", "c", "d", "e", "f"],
            reason="too many",
        )


# --- CitationAttributionScore ---------------------------------------------


def test_citation_attribution_happy() -> None:
    s = CitationAttributionScore(
        score=0.5, n_markers=2, n_correct=1, incorrect_markers=[2], reason="one wrong"
    )
    assert s.n_correct <= s.n_markers


def test_citation_attribution_rejects_inconsistent_counts() -> None:
    with pytest.raises(ValidationError):
        CitationAttributionScore(score=1.0, n_markers=1, n_correct=2, reason="bad")


# --- AnswerRelevancyScore --------------------------------------------------


@pytest.mark.parametrize(
    ("label", "score"),
    [("relevant", 1.0), ("partial", 0.5), ("off_topic", 0.0)],
)
def test_answer_relevancy_label_score_pairs(label: str, score: float) -> None:
    s = AnswerRelevancyScore(label=label, score=score, reason="ok")  # type: ignore[arg-type]
    assert s.label == label


def test_answer_relevancy_rejects_label_score_mismatch() -> None:
    with pytest.raises(ValidationError):
        AnswerRelevancyScore(label="relevant", score=0.5, reason="wrong score")


def test_answer_relevancy_rejects_unknown_label() -> None:
    with pytest.raises(ValidationError):
        AnswerRelevancyScore(label="kind_of", score=0.5, reason="bad")  # type: ignore[arg-type]


# --- ConflictDisclosureScore -----------------------------------------------


def test_conflict_disclosure_not_applicable() -> None:
    s = ConflictDisclosureScore(applicable=False, label="n/a", score=None, reason="non-rule_b")
    assert s.score is None


def test_conflict_disclosure_applicable_yes() -> None:
    s = ConflictDisclosureScore(applicable=True, label="yes", score=1.0, reason="ok")
    assert s.score == 1.0


def test_conflict_disclosure_rejects_inconsistent_applicable_false() -> None:
    with pytest.raises(ValidationError):
        ConflictDisclosureScore(applicable=False, label="yes", score=1.0, reason="bad")


def test_conflict_disclosure_rejects_applicable_with_na_label() -> None:
    with pytest.raises(ValidationError):
        ConflictDisclosureScore(applicable=True, label="n/a", score=None, reason="bad")


# --- RuleAPurityScore ------------------------------------------------------


def test_rule_a_purity_clean() -> None:
    s = RuleAPurityScore(label="clean", score=1.0, reason="ok")
    assert s.score == 1.0


def test_rule_a_purity_leaked_requires_sentences() -> None:
    with pytest.raises(ValidationError):
        RuleAPurityScore(label="leaked", score=0.0, leaked_sentences=[], reason="needs entries")


def test_rule_a_purity_na() -> None:
    s = RuleAPurityScore(label="n/a", score=None, reason="clarify turn")
    assert s.score is None


# --- CompletenessScore -----------------------------------------------------


@pytest.mark.parametrize(
    ("label", "score"),
    [
        ("complete", 1.0),
        ("partial", 0.5),
        ("shallow", 0.0),
    ],
)
def test_completeness_label_score_pairs(label: str, score: float) -> None:
    s = CompletenessScore(label=label, score=score, reason="ok")  # type: ignore[arg-type]
    assert s.score == score


def test_completeness_na() -> None:
    s = CompletenessScore(label="n/a", score=None, reason="refusal")
    assert s.score is None


# --- JudgeResult -----------------------------------------------------------


def _ok_judge_result(qid: str = "q01") -> JudgeResult:
    return JudgeResult(
        id=qid,
        judge_model="claude-opus-4-7",
        judge_prompt_hash="abc12345",
        judged_at=datetime(2026, 5, 11, 12, 0, 0, tzinfo=UTC),
        faithfulness=FaithfulnessScore(
            score=1.0, n_sentences=2, n_supported=2, reason="all supported"
        ),
        answer_relevancy=AnswerRelevancyScore(label="relevant", score=1.0, reason="on-topic"),
        conflict_disclosure=ConflictDisclosureScore(
            applicable=False, label="n/a", score=None, reason="not rule_b"
        ),
        rule_a_purity=RuleAPurityScore(label="clean", score=1.0, reason="no leaks"),
        citation_attribution=CitationAttributionScore(
            score=1.0, n_markers=2, n_correct=2, reason="both correct"
        ),
        completeness=CompletenessScore(label="complete", score=1.0, reason="covers all points"),
    )


def test_judge_result_roundtrip() -> None:
    r = _ok_judge_result()
    blob = r.model_dump_json()
    r2 = JudgeResult.model_validate_json(blob)
    assert r2.id == r.id
    assert r2.metric_scores() == r.metric_scores()


def test_judge_result_metric_scores_view() -> None:
    r = _ok_judge_result()
    scores = r.metric_scores()
    assert set(scores) == set(METRIC_NAMES)
    assert scores["faithfulness"] == 1.0
    assert scores["conflict_disclosure"] is None
