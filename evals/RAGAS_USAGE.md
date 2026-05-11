# Ragas usage — what we use, what we skip, and why

This document records the deliberate choices behind how this project uses
[Ragas](https://github.com/explodinggradients/ragas) for the evaluation
suite. It exists because a reviewer should be able to verify, in two minutes,
that we (a) understand the framework, (b) chose it over alternatives for stated
reasons, and (c) consciously skipped features that would have burned extra
tokens or pulled in transitive dependencies we didn't need.

## What this eval suite does

For each hand-authored question in `evals/golden_set.yaml`, we:

1. Run `app.agent.run()` end-to-end against the live retriever (BM25 over the
   conviction corpus) and the configured LLM provider.
2. Convert the resulting `AgentResult` into a Ragas `SingleTurnSample` whose
   metadata carries our test-case attributes (`bucket`, `expected_passage_ids`,
   `expected_out_of_scope`, etc.) plus a snapshot of the resolver's per-citation
   outcomes.
3. Hand those samples to four custom Ragas metrics (`anchor_rate`,
   `citation_precision`, `refusal_correctness`, `general_knowledge_correctness`)
   plus pre-computed per-question token / tool-call / duration counters.
4. Persist three artefacts to `evals/results/`:
   - `…csv` — the per-question DataFrame from `EvaluationResult.to_pandas()`.
   - `…json` — run metadata (model, reasoning_effort, git SHA, settings
     snapshot) plus aggregate metrics.
   - `…md` — human-readable summary tables, embeddable in the README.

`evals.compare` diffs two CSVs side by side: aggregate deltas, regressions
(passing in A, failing in B), improvements, and per-bucket breakdown.

## Features we use

### `@discrete_metric` and `@numeric_metric` decorators

Each of our four custom metrics is a short function with one of these
decorators. The decorator handles the integration with `evaluate()` and the
result shape; we just write the comparison logic.

Why: the API is five-line short, returns a `MetricResult(value, reason)`, and
needs neither a subclass nor an LLM client. Boilerplate-free.

### `SingleTurnSample`

The contract every Ragas metric reads from. We populate:

- `user_input` — the user question.
- `response` — the agent's final answer text (or the clarifying question).
- `retrieved_contexts` — list of the passage texts the agent cited.
- `reference` — optional gold answer (we don't set it; we rely on
  `expected_passage_ids` instead).
- `additional_metadata` — our payload: `bucket`, `language`,
  `expected_passage_ids`, `expected_out_of_scope`,
  `expected_general_knowledge`, `expected_conflict_mention`, plus a serialized
  copy of the resolver entries the custom metrics need to compute scores.

Why: it's the standard shape that decouples our custom metrics from the
specifics of `AgentResult`. If we ever swap Ragas for something else, the
metrics layer ports cleanly; the runner is the only piece that knows about
`AgentResult`.

### `EvaluationDataset`

Wrapper around `list[SingleTurnSample]` that `evaluate()` consumes. Supports
filtering and slicing, which we use for the `--limit` and `--bucket` CLI flags.

### `evaluate()`

The orchestrator that runs each metric over each sample. Returns an
`EvaluationResult` with a `.to_pandas()` method that flattens everything to a
DataFrame — one row per sample, one column per metric.

Why: it batches and parallelizes for free; if we wrote our own loop we'd
duplicate that work for no gain.

### `EvaluationResult.to_pandas()`

Returns the canonical per-question DataFrame. We append our pre-computed
per-question columns (`prompt_tokens`, `completion_tokens`, `cached_tokens`,
`reasoning_tokens`, `tool_calls`, `duration_ms`, `language`, `bucket`) onto it
before writing the CSV.

Why: pandas is already a peer dependency of Ragas, and `pd.merge` makes
cross-run comparison trivial. No second framework needed for reports.

## Features we deliberately skip

### Built-in LLM-judge metrics (`Faithfulness`, `AnswerRelevancy`, `ContextPrecision`, `FactualCorrectness`)

Why: each one calls the LLM 1–3 times per question. They are subjectively
scored, vary between runs at the same temperature, and this project pins
the deterministic anchor rate as the headline metric. Activating them would
roughly double the provider-token footprint for signal we don't need at this
stage.

These are available behind the future `--with-judge` flag (not yet wired).
The runner is structured so that adding them is a one-line change to the
metric list.

### `LangchainLLMWrapper`

Only needed for the LLM-judge metrics. We don't use those, so we don't pay the
Langchain transitive-dependency tax.

### Synthetic data generation (`TestsetGenerator`)

The golden set was hand-authored after reading the corpus end-to-end. For 30
questions in a domain (Brazilian fixed income, mostly) where synthetic
generators struggle with bilingual specificity (PT/EN/ES), human authorship was
more direct, more honest, and produced a higher floor of difficulty per question.
Synthetic generation is an option once the corpus reaches hundreds of
documents and the manual curation effort no longer scales.

### Ragas Cloud (`app.ragas.io`)

We persist results to `evals/results/` locally. Cloud hosting is convenient
for teams comparing runs across machines, but we don't need that for a
single-author interview project. Local CSVs work cleanly with `git` and the
`evals.compare` script.

### Langchain / LlamaIndex evaluator chains

Our agent is a native Python function (`app.agent.run`). The chain adapters
exist for users running their pipeline inside one of those frameworks; we
have no reason to detour through them.

## How to add a new metric

1. Write a function decorated with `@numeric_metric` (continuous score) or
   `@discrete_metric` (categorical, e.g. correct/incorrect).
2. The function takes a `SingleTurnSample` and returns a
   `MetricResult(value=…, reason=…)`.
3. Add it to the metric list inside `evals/run.py::_metrics()`.
4. Add a unit test in `tests/eval/test_metrics.py` that synthesises a
   minimal `SingleTurnSample` and asserts the expected score.

If the metric needs an LLM judge, add it behind the `--with-judge` CLI flag
so the default run stays deterministic and lightweight.

## How to add an LLM-judge metric later

When the project decides to take the LLM-judge step:

1. `uv add langchain langchain-openai` — required by Ragas's LLM-based metrics.
2. Construct an `evaluator_llm = LangchainLLMWrapper(ChatOpenAI(model=…))`.
3. Pass it through `evaluate(…, llm=evaluator_llm)` and add the built-in
   metrics (e.g. `Faithfulness()`) to the metric list inside the
   `--with-judge` branch.
4. The runner already records reasoning_effort and model snapshots per run,
   so an LLM-judge regression is comparable to a non-judge run.
