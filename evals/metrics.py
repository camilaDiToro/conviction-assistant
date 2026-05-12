"""Custom deterministic metrics for the eval suite.

These use Ragas's ``@discrete_metric`` / ``@numeric_metric`` decorators
so the metric objects own their name + allowed-value contracts and
return a ``MetricResult(value, reason)``. They are invoked directly
(``metric.score(...)``) by ``evals.run`` — we deliberately do not pass
them through ``ragas.evaluate`` because that pathway expects
``Metric``-class instances and is overkill for our 30-question deterministic
suite. See ``evals/RAGAS_USAGE.md`` for the full rationale.

Each metric reads its inputs from kwargs, never from an LLM. They are
side-effect-free, pure functions over the per-question data the runner
already has.

Shapes the metrics consume (kept dict-shaped so the runner can
hand-build them without coupling to ``AgentResult``):

- ``citations``: ``list[dict]`` with keys ``passage_id``, ``failure_reason``
  (None on anchor, str on failure).
- ``output``: the agent's structured output. For an ``AnswerOutput``,
  carries ``kind="answer"``, ``out_of_scope``, ``general_knowledge_used``,
  ``general_knowledge_section``, ``answer``. For a clarifying question,
  ``kind="clarifying_question"``, ``question``.
"""

import re
from typing import Any

from ragas.metrics import MetricResult, discrete_metric, numeric_metric


@numeric_metric(name="anchor_rate", allowed_values=(0.0, 1.0))
def anchor_rate(citations: list[dict[str, Any]]) -> MetricResult:
    """Headline metric: fraction of cited quotes that resolved to an
    offset in the cited passage. ``failure_reason is None`` means anchored.

    A question with zero citations gets a 0 — refusal/clarify paths
    bypass this metric in the runner by filtering the aggregate denominator
    on answer-bucket questions only.
    """
    if not citations:
        return MetricResult(value=0.0, reason="no citations emitted")
    anchored = sum(1 for c in citations if c.get("failure_reason") is None)
    rate = anchored / len(citations)
    return MetricResult(
        value=rate,
        reason=f"{anchored}/{len(citations)} citations anchored",
    )


@numeric_metric(name="citation_precision", allowed_values=(0.0, 1.0))
def citation_precision(
    citations: list[dict[str, Any]], expected_passage_ids: list[str]
) -> MetricResult:
    """For questions with declared ``expected_passage_ids``, the fraction
    of the expected set that the agent actually cited. Extra citations
    (anchored but not in the expected list) are treated as neutral and do
    **not** lower the score — the golden often under-specifies which
    passages are valid, so penalising any cite outside the list misreads
    the agent's behaviour. Returns 1.0 when the golden has no expected
    ids (metric "doesn't apply")."""
    if not expected_passage_ids:
        return MetricResult(value=1.0, reason="expected_passage_ids unset; metric not applicable")
    if not citations:
        return MetricResult(value=0.0, reason="no citations to score")
    expected = set(expected_passage_ids)
    cited_ids = {c.get("passage_id") for c in citations}
    matched = expected & cited_ids
    extras = len(cited_ids - expected)
    rate = len(matched) / len(expected)
    return MetricResult(
        value=rate,
        reason=(
            f"{len(matched)}/{len(expected)} expected ids cited"
            f" ({extras} extra cite{'s' if extras != 1 else ''}, not penalised)"
        ),
    )


@numeric_metric(name="citation_recall", allowed_values=(0.0, 1.0))
def citation_recall(
    citations: list[dict[str, Any]], expected_passage_ids: list[str]
) -> MetricResult:
    """Fraction of ``expected_passage_ids`` that show up in the cited set.

    Pairs with ``citation_precision`` to give the IR view of citation
    quality. Returns 1.0 when the golden has no expected ids ("not
    applicable", matching precision's convention)."""
    if not expected_passage_ids:
        return MetricResult(value=1.0, reason="expected_passage_ids unset; metric not applicable")
    cited_ids = {c.get("passage_id") for c in citations}
    expected = set(expected_passage_ids)
    found = expected & cited_ids
    rate = len(found) / len(expected)
    return MetricResult(
        value=rate,
        reason=f"{len(found)}/{len(expected)} expected ids cited",
    )


@discrete_metric(name="refusal_correctness", allowed_values=["correct", "incorrect", "n/a"])
def refusal_correctness(output: dict[str, Any], expected_out_of_scope: bool) -> MetricResult:
    """Two-direction refusal check.

    - ``expected_out_of_scope=true``: the agent must set ``out_of_scope=true``
      (clarifying-question is ``incorrect``).
    - ``expected_out_of_scope=false``: the agent must NOT refuse. A
      clarifying-question output is ``n/a`` (handled by
      ``clarify_correctness``); ``out_of_scope=true`` on an in-scope
      question is a false refusal → ``incorrect``.
    """
    kind = output.get("kind")
    if expected_out_of_scope:
        if kind == "clarifying_question":
            return MetricResult(value="incorrect", reason="agent asked a clarifying question")
        if bool(output.get("out_of_scope")):
            return MetricResult(value="correct", reason="agent refused as expected")
        return MetricResult(value="incorrect", reason="agent answered when it should have refused")
    if kind == "clarifying_question":
        return MetricResult(value="n/a", reason="clarifying-question routed to clarify_correctness")
    if bool(output.get("out_of_scope")):
        return MetricResult(value="incorrect", reason="false refusal on in-scope question")
    return MetricResult(value="correct", reason="agent did not falsely refuse")


@discrete_metric(
    name="general_knowledge_correctness", allowed_values=["correct", "incorrect", "n/a"]
)
def general_knowledge_correctness(
    output: dict[str, Any], expected_general_knowledge: bool
) -> MetricResult:
    """Rule A check: did the agent use the ``general_knowledge_section``
    only when the golden allows it? Two failure modes:

    1. ``expected_general_knowledge=false`` but the agent emitted a
       general-knowledge section → false positive (made stuff up).
    2. ``expected_general_knowledge=true`` but the agent didn't emit one
       → false negative (missed the chance to be helpful inside the
       boundary). We score 'incorrect' for both.

    Clarifying questions and refusals are 'n/a' (they don't carry the
    field meaningfully).
    """
    if output.get("kind") != "answer":
        return MetricResult(value="n/a", reason="not an answer turn")
    if output.get("out_of_scope"):
        return MetricResult(value="n/a", reason="answer was out_of_scope; rule A does not apply")
    used = bool(output.get("general_knowledge_used"))
    if used == expected_general_knowledge:
        return MetricResult(
            value="correct",
            reason=f"general_knowledge_used={used} matches expected={expected_general_knowledge}",
        )
    return MetricResult(
        value="incorrect",
        reason=f"general_knowledge_used={used} but expected={expected_general_knowledge}",
    )


@discrete_metric(name="clarify_correctness", allowed_values=["correct", "incorrect", "n/a"])
def clarify_correctness(output: dict[str, Any], bucket: str) -> MetricResult:
    """Did the agent ask for clarification iff the bucket calls for it?

    - bucket=clarify: output must be ``clarifying_question``.
    - bucket!=clarify: output must be ``answer``; a clarifying-question
      here is a wrongful clarification → ``incorrect``.
    """
    kind = output.get("kind")
    if bucket == "clarify":
        if kind == "clarifying_question":
            return MetricResult(value="correct", reason="agent clarified as expected")
        return MetricResult(value="incorrect", reason=f"clarify bucket but kind={kind!r}")
    if kind == "clarifying_question":
        return MetricResult(
            value="incorrect", reason=f"wrongful clarifying question on bucket={bucket!r}"
        )
    return MetricResult(value="n/a", reason="non-clarify bucket and agent did not clarify")


@discrete_metric(name="meets_min_citations", allowed_values=["correct", "incorrect", "n/a"])
def meets_min_citations(citations: list[dict[str, Any]], must_cite_at_least: int) -> MetricResult:
    """Did the agent emit at least ``must_cite_at_least`` distinct citations?

    ``must_cite_at_least == 0`` ⇒ ``n/a`` (refusal/clarify paths).
    Counts distinct ``passage_id``s, not raw citation entries, so emitting
    two citations against the same passage does not satisfy a min of 2.
    """
    if must_cite_at_least <= 0:
        return MetricResult(value="n/a", reason="must_cite_at_least=0; metric not applicable")
    distinct = len({c.get("passage_id") for c in citations})
    if distinct >= must_cite_at_least:
        return MetricResult(
            value="correct", reason=f"{distinct} distinct passage_ids ≥ {must_cite_at_least}"
        )
    return MetricResult(
        value="incorrect", reason=f"{distinct} distinct passage_ids < {must_cite_at_least}"
    )


_CONFLICT_MARKERS: tuple[str, ...] = (
    "diverg",   # PT/EN "divergem"/"divergen"/"diverge"/"divergence"
    "discord",  # PT "discordam"
    "disagree",  # EN "convictions disagree"
    "difier",   # ES "difieren"
    "conflit",  # PT "conflitam"/EN "conflict"
)


@discrete_metric(name="conflict_disclosure_det", allowed_values=["correct", "incorrect", "n/a"])
def conflict_disclosure_det(
    output: dict[str, Any], expected_conflict_mention: bool
) -> MetricResult:
    """Rule B semantic: did the agent emit ``conflict_detected`` matching
    the golden, with a ``conflict_statement`` that names the
    disagreement using a canonical marker phrase?

    Replaces the LLM-as-judge ``conflict_disclosure`` rubric. The
    structured field is the source of truth: ``AnswerOutput`` already
    validates that ``conflict_detected=true`` requires a non-empty
    ``conflict_statement``; we additionally check that the statement
    contains a literal disagreement marker so an analyst scanning the
    audit log gets an unambiguous cue.

    Behavior:
    - ``expected_conflict_mention=false`` ⇒ ``n/a`` (not Rule B).
    - Clarifying / out_of_scope output ⇒ ``n/a``.
    - ``conflict_detected=false`` on a Rule B golden ⇒ ``incorrect``.
    - ``conflict_detected=true`` but the statement lacks a marker
      phrase ⇒ ``incorrect``.
    - Otherwise ⇒ ``correct``.
    """
    if output.get("kind") != "answer":
        return MetricResult(value="n/a", reason="not an answer turn")
    if not expected_conflict_mention:
        return MetricResult(value="n/a", reason="expected_conflict_mention=false; not applicable")
    detected = bool(output.get("conflict_detected"))
    if not detected:
        return MetricResult(
            value="incorrect",
            reason="expected conflict_detected=true but agent emitted false",
        )
    statement = (output.get("conflict_statement") or "").strip().lower()
    if not any(marker in statement for marker in _CONFLICT_MARKERS):
        return MetricResult(
            value="incorrect",
            reason=(
                f"conflict_detected=true but statement lacks a disagreement marker: "
                f"{statement[:120]!r}"
            ),
        )
    return MetricResult(value="correct", reason="conflict_detected=true with canonical marker")


@discrete_metric(name="conflict_min_citations", allowed_values=["correct", "incorrect", "n/a"])
def conflict_min_citations(
    citations: list[dict[str, Any]], expected_conflict_mention: bool
) -> MetricResult:
    """Rule B precondition: when convictions disagree, the agent must
    cite at least two distinct passages (one per side). Pairs with
    :func:`conflict_disclosure_det` (semantic check) to fully replace
    the previous LLM-judge ``conflict_disclosure`` rubric.
    """
    if not expected_conflict_mention:
        return MetricResult(value="n/a", reason="expected_conflict_mention=false; not applicable")
    distinct = len({c.get("passage_id") for c in citations})
    if distinct >= 2:
        return MetricResult(
            value="correct", reason=f"{distinct} distinct passage_ids covers a conflict"
        )
    return MetricResult(
        value="incorrect",
        reason=f"{distinct} distinct passage_ids — cannot represent a conflict",
    )


@discrete_metric(name="language_match", allowed_values=["correct", "incorrect", "n/a"])
def language_match(output: dict[str, Any], expected_language: str) -> MetricResult:
    """Did the agent answer in the user's language?

    Runs over ``output.answer`` for answer turns, ``output.question`` for
    clarifying turns. Returns ``n/a`` when there is no text to detect.
    """
    text = (output.get("answer") or output.get("question") or "").strip()
    if not text:
        return MetricResult(value="n/a", reason="no text to detect language on")
    detected = _detect_language(text)
    if detected == expected_language:
        return MetricResult(value="correct", reason=f"detected={detected} matches expected")
    return MetricResult(
        value="incorrect", reason=f"detected={detected} but expected={expected_language}"
    )


# --- helpers ----------------------------------------------------------------


_WORD_RE = re.compile(r"[a-zà-ÿ]+", re.IGNORECASE)

# Discriminative tokens per language. Picked for low cross-language overlap;
# combined with diacritic signals below for short-text robustness.
_PT_TOKENS: frozenset[str] = frozenset(
    {
        "não",
        "é",
        "também",
        "pelo",
        "pela",
        "isto",
        "isso",
        "muito",
        "está",
        "são",
        "uma",
        "um",
        "como",
        "no",
        "na",
        "nos",
        "nas",
        "do",
        "da",
        "dos",
        "das",
        "com",
        "para",
        "que",
        "ser",
        "ter",
        "fazer",
        "tributação",
        "renda",
        "fundo",
        "fundos",
    }
)
_ES_TOKENS: frozenset[str] = frozenset(
    {
        "el",
        "la",
        "los",
        "las",
        "del",
        "una",
        "uno",
        "esto",
        "eso",
        "muy",
        "está",
        "son",
        "como",
        "por",
        "para",
        "que",
        "ser",
        "tener",
        "hacer",
        "qué",
        "cómo",
        "tributación",
        "renta",
        "fondo",
        "fondos",
        "según",
    }
)
_EN_TOKENS: frozenset[str] = frozenset(
    {
        "the",
        "of",
        "and",
        "is",
        "in",
        "to",
        "for",
        "with",
        "on",
        "at",
        "as",
        "by",
        "from",
        "that",
        "this",
        "which",
        "are",
        "was",
        "were",
        "have",
        "has",
        "be",
        "an",
        "or",
        "but",
        "not",
        "it",
    }
)
_PT_DIACRITICS = "ãõçÃÕÇ"
_ES_DIACRITICS = "ñ¿¡Ñ"


def _detect_language(text: str) -> str:
    """Light-weight PT/ES/EN detector. Diacritic signals are weighted 3×
    a stop-word hit; in a tie EN wins (the corpus is mostly PT/EN, so a
    no-signal short string is more likely EN-leaning fragments)."""
    lower = text.lower()
    pt_diac = sum(lower.count(c) for c in _PT_DIACRITICS)
    es_diac = sum(lower.count(c) for c in _ES_DIACRITICS)

    words = _WORD_RE.findall(lower)
    pt_hits = sum(1 for w in words if w in _PT_TOKENS)
    es_hits = sum(1 for w in words if w in _ES_TOKENS)
    en_hits = sum(1 for w in words if w in _EN_TOKENS)

    scores = {
        "pt": pt_diac * 3 + pt_hits,
        "es": es_diac * 3 + es_hits,
        "en": en_hits,
    }
    # Tie-break order: pt > es > en. Stable when scores match (e.g. empty text
    # gives all zeros — the metric guards against that upstream).
    return max(scores, key=lambda k: (scores[k], -["pt", "es", "en"].index(k)))


__all__ = [
    "anchor_rate",
    "citation_precision",
    "citation_recall",
    "clarify_correctness",
    "conflict_disclosure_det",
    "conflict_min_citations",
    "general_knowledge_correctness",
    "language_match",
    "meets_min_citations",
    "refusal_correctness",
]
