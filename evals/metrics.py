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
  ``general_knowledge_section``. For a clarifying question, ``kind="clarifying_question"``.
"""

from typing import Any

from ragas.metrics import MetricResult, discrete_metric, numeric_metric


@numeric_metric(name="anchor_rate", allowed_values=(0.0, 1.0))
def anchor_rate(citations: list[dict[str, Any]]) -> MetricResult:
    """Headline metric: fraction of cited quotes that resolved to an
    offset in the cited passage. ``failure_reason is None`` means anchored.

    A question with zero citations gets a 0 — refusal/clarify paths
    bypass this metric in the runner by setting must_cite_at_least=0.
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
    of cited passage ids that are in the expected set. Returns 1.0 when
    the golden has no expected ids (the metric "doesn't apply")."""
    if not expected_passage_ids:
        return MetricResult(value=1.0, reason="expected_passage_ids unset; metric not applicable")
    if not citations:
        return MetricResult(value=0.0, reason="no citations to score")
    expected = set(expected_passage_ids)
    cited_ids = [c.get("passage_id") for c in citations]
    correct = sum(1 for pid in cited_ids if pid in expected)
    rate = correct / len(citations)
    return MetricResult(
        value=rate,
        reason=f"{correct}/{len(citations)} citations match expected ids",
    )


@discrete_metric(name="refusal_correctness", allowed_values=["correct", "incorrect", "n/a"])
def refusal_correctness(output: dict[str, Any], expected_out_of_scope: bool) -> MetricResult:
    """For questions marked ``expected_out_of_scope=true``, the agent's
    structured output must carry ``out_of_scope=true`` (or be a
    clarifying-question). Returns ``"n/a"`` when the golden does not
    expect a refusal."""
    if not expected_out_of_scope:
        return MetricResult(value="n/a", reason="expected_out_of_scope is false")
    kind = output.get("kind")
    if kind == "clarifying_question":
        return MetricResult(value="incorrect", reason="agent asked a clarifying question")
    refused = bool(output.get("out_of_scope"))
    if refused:
        return MetricResult(value="correct", reason="agent refused as expected")
    return MetricResult(value="incorrect", reason="agent answered when it should have refused")


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


__all__ = [
    "anchor_rate",
    "citation_precision",
    "general_knowledge_correctness",
    "refusal_correctness",
]
