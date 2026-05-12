# Ragas usage — what we actually use and why

This is a short, accurate account of how the suite uses Ragas. The
previous version of this doc described a `SingleTurnSample` /
`EvaluationDataset` / `evaluate()` / `to_pandas()` flow that did not
exist in the code. This rewrite reflects the implementation.

## What we use

**Only the two metric decorators**: `@discrete_metric` and
`@numeric_metric` from `ragas.metrics`. They wrap a pure function and
give us:

- A `MetricResult(value, reason)` return shape with type-checked
  `allowed_values`.
- A `.score(...)` callable so the runner invokes the metric with the
  kwargs it already has on hand.

That's it. The full surface lives in `evals/metrics.py`:

```python
@numeric_metric(name="anchor_rate", allowed_values=(0.0, 1.0))
def anchor_rate(citations: list[dict[str, Any]]) -> MetricResult: ...

@discrete_metric(name="refusal_correctness",
                 allowed_values=["correct", "incorrect", "n/a"])
def refusal_correctness(output: dict[str, Any],
                        expected_out_of_scope: bool) -> MetricResult: ...
```

Each metric is a pure function over dicts the runner hand-builds — no
LLM client, no I/O, no globals.

## What we deliberately do not use

| Ragas feature | Status | Why |
|---|---|---|
| `SingleTurnSample` | not imported | adds shape ceremony without changing what we compute |
| `EvaluationDataset` | not imported | same |
| `ragas.evaluate()` | not called | designed for `Metric` subclasses; overkill for 30 deterministic questions |
| `EvaluationResult.to_pandas()` | not called | we build the DataFrame from `_QuestionRow.as_dict()` instead |
| `Faithfulness` / `AnswerRelevancy` / `ContextPrecision` / `FactualCorrectness` | not wired | LLM-judge metrics that double provider cost and drift between runs |
| `LangchainLLMWrapper` | not imported | only needed for the LLM-judge metrics |
| `TestsetGenerator` | not imported | 30 hand-authored questions; revisit once the corpus is large |
| Ragas Cloud | not used | local CSV + git is enough for a single-author repo |

## Consequence: faithfulness is not directly measured

The brief calls faithfulness "the core challenge". The deterministic
metrics here cover citation anchoring, citation precision/recall,
language match, refusal/clarify correctness, and the rule-B
minimum-citation precondition — but **none of them verifies that the
answer text is actually supported by the cited passages**.

For that signal, the project ships a separate **LLM-as-judge layer**
under `evals/judge/` (see that module's docstrings). The judge runs
manually from a code assistant against the trace JSONL the deterministic
runner already produces. There is no Ragas, subprocess, or CLI code path
that calls a judge model. The manually produced judge JSONL validates
against a fixed Pydantic schema and feeds into a combined report
alongside the deterministic numbers.

The split is intentional: the deterministic suite gives a fast,
reproducible, token-free signal on every CI run; the judge gives a
deeper, model-comparable faithfulness/relevancy/attribution signal on
demand.

## How to add a new deterministic metric

1. Write a function in `evals/metrics.py` decorated with
   `@numeric_metric` (continuous) or `@discrete_metric` (categorical).
2. Pull inputs from kwargs the runner already has — never reach for
   an LLM client.
3. Wire it into `_QuestionRow` and `_row_from_result` in `evals/run.py`.
4. Add a unit test to `tests/eval/test_metrics.py` exercising every
   branch.
5. Add the column to `_REQUIRED_COLUMNS` in `evals/report.py` so
   `write_run` enforces its presence.

## Could we drop Ragas entirely?

Yes — the decorators contribute ~30 lines of value. A plain dataclass
`MetricResult` and bare functions would be equivalent and remove a
transitive that pulls in `datasets`, `langchain-core`, etc. It is on
the backlog. The reason it has not happened: the dependency is already
in the lockfile, the decorators are pleasant to use, and removing
Ragas should ideally land at the same time as wiring its
`Faithfulness` metric (so we make the right keep-or-remove call with
the judge layer's needs known).
