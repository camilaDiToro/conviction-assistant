"""Pydantic schema for one LLM-as-judge verdict.

Every metric exposes a nullable ``score in [0, 1]`` so the aggregator
computes one mean per metric — discrete labels map to fixed numeric
anchors via the ``_LABEL_SCORES`` tables. Reasons are bounded to keep
the JSONL diffable.

Cross-model comparison contract: two judge runs are only comparable
when their ``(judge_model, judge_prompt_hash)`` match. The aggregator
refuses to diff mismatched signatures.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

# --- numeric metrics --------------------------------------------------------

_REASON_MAX = 240
_LIST_MAX = 5


class FaithfulnessScore(BaseModel):
    """Sentence-level entailment: fraction of `answer` sentences that
    are supported by the cited passages.

    ``score = n_supported / n_sentences`` when ``n_sentences > 0``;
    falls back to 1.0 when ``n_sentences == 0`` (e.g. refusal turn with
    no answer text — the judge should mark this as ``n/a`` upstream
    instead, so an all-zero record is suspect).
    """

    model_config = ConfigDict(extra="forbid")

    score: float = Field(ge=0.0, le=1.0)
    n_sentences: int = Field(ge=0)
    n_supported: int = Field(ge=0)
    unsupported: list[str] = Field(default_factory=list, max_length=_LIST_MAX)
    reason: str = Field(max_length=_REASON_MAX)

    @model_validator(mode="after")
    def _check(self) -> "FaithfulnessScore":
        if self.n_supported > self.n_sentences:
            raise ValueError(
                f"n_supported={self.n_supported} cannot exceed n_sentences={self.n_sentences}"
            )
        return self


class CitationAttributionScore(BaseModel):
    """For each ``[N]`` marker in the answer, did citation N actually
    support the surrounding claim?

    ``score = n_correct / n_markers`` when ``n_markers > 0``; 1.0 when
    the answer has no markers (the metric trivially holds).
    """

    model_config = ConfigDict(extra="forbid")

    score: float = Field(ge=0.0, le=1.0)
    n_markers: int = Field(ge=0)
    n_correct: int = Field(ge=0)
    incorrect_markers: list[int] = Field(default_factory=list)
    reason: str = Field(max_length=_REASON_MAX)

    @model_validator(mode="after")
    def _check(self) -> "CitationAttributionScore":
        if self.n_correct > self.n_markers:
            raise ValueError(f"n_correct={self.n_correct} cannot exceed n_markers={self.n_markers}")
        return self


# --- discrete metrics with label↔score consistency --------------------------

_RELEVANCY_SCORES: dict[str, float] = {"relevant": 1.0, "partial": 0.5, "off_topic": 0.0}
_PURITY_SCORES: dict[str, float | None] = {"clean": 1.0, "leaked": 0.0, "n/a": None}
_COMPLETENESS_SCORES: dict[str, float | None] = {
    "complete": 1.0,
    "partial": 0.5,
    "shallow": 0.0,
    "n/a": None,
}


def _check_label_score(label: str, score: float | None, table: dict[str, float | None]) -> None:
    expected = table[label]
    if expected is None:
        if score is not None:
            raise ValueError(f"label={label!r} requires score=None, got {score!r}")
    else:
        if score is None or abs(score - expected) > 1e-9:
            raise ValueError(f"label={label!r} requires score={expected}, got {score!r}")


class AnswerRelevancyScore(BaseModel):
    """Does the answer address the user's question (regardless of
    grounding)? ``relevant`` = on-topic and complete-shaped;
    ``partial`` = partially addresses; ``off_topic`` = does not address
    the question at all.
    """

    model_config = ConfigDict(extra="forbid")

    label: Literal["relevant", "partial", "off_topic"]
    score: float = Field(ge=0.0, le=1.0)
    reason: str = Field(max_length=_REASON_MAX)

    @model_validator(mode="after")
    def _check(self) -> "AnswerRelevancyScore":
        _check_label_score(self.label, self.score, _RELEVANCY_SCORES)  # type: ignore[arg-type]
        return self


class RuleAPurityScore(BaseModel):
    """Rule A semantic: does ``answer`` contain general-knowledge text
    that should have lived in ``general_knowledge_section``?

    ``n/a`` only when the output is a clarifying-question or an
    out-of-scope refusal (Rule A does not apply to those shapes).
    """

    model_config = ConfigDict(extra="forbid")

    label: Literal["clean", "leaked", "n/a"]
    score: float | None
    leaked_sentences: list[str] = Field(default_factory=list, max_length=_LIST_MAX)
    reason: str = Field(max_length=_REASON_MAX)

    @model_validator(mode="after")
    def _check(self) -> "RuleAPurityScore":
        _check_label_score(self.label, self.score, _PURITY_SCORES)
        if self.label == "leaked" and not self.leaked_sentences:
            raise ValueError("label='leaked' requires at least one entry in leaked_sentences")
        return self


class CompletenessScore(BaseModel):
    """Within the cited passages, did the answer cover the substantive
    points the user asked about? ``complete`` = covers the main points;
    ``partial`` = covers some; ``shallow`` = one-line gloss over a
    multi-point question.

    ``n/a`` for refusals / clarifying questions / when no passages were
    cited (nothing to be complete about).
    """

    model_config = ConfigDict(extra="forbid")

    label: Literal["complete", "partial", "shallow", "n/a"]
    score: float | None
    missing: str = Field(default="", max_length=_REASON_MAX)
    reason: str = Field(max_length=_REASON_MAX)

    @model_validator(mode="after")
    def _check(self) -> "CompletenessScore":
        _check_label_score(self.label, self.score, _COMPLETENESS_SCORES)
        return self


# --- container --------------------------------------------------------------


class JudgeResult(BaseModel):
    """One judge verdict for one golden question.

    ``judge_model`` and ``judge_prompt_hash`` are stamped per record so
    cross-model comparison can refuse to diff mismatched signatures.
    """

    model_config = ConfigDict(extra="forbid")

    id: str
    judge_model: str
    judge_prompt_hash: str
    judged_at: datetime
    faithfulness: FaithfulnessScore
    answer_relevancy: AnswerRelevancyScore
    rule_a_purity: RuleAPurityScore
    citation_attribution: CitationAttributionScore
    completeness: CompletenessScore

    def metric_scores(self) -> dict[str, float | None]:
        """Flat {metric_name: score | None} view for the aggregator."""
        return {
            "faithfulness": self.faithfulness.score,
            "answer_relevancy": self.answer_relevancy.score,
            "rule_a_purity": self.rule_a_purity.score,
            "citation_attribution": self.citation_attribution.score,
            "completeness": self.completeness.score,
        }


METRIC_NAMES: tuple[str, ...] = (
    "faithfulness",
    "answer_relevancy",
    "rule_a_purity",
    "citation_attribution",
    "completeness",
)


__all__ = [
    "METRIC_NAMES",
    "AnswerRelevancyScore",
    "CitationAttributionScore",
    "CompletenessScore",
    "FaithfulnessScore",
    "JudgeResult",
    "RuleAPurityScore",
]
