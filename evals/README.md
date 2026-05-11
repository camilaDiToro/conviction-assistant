# Eval suite

Hand-authored golden set + deterministic metrics + runner + comparator.
The headline metric is **anchor rate** — what fraction of cited quotes
resolved to an offset region in the cited passage.

See `RAGAS_USAGE.md` for which Ragas features the suite uses and why.

## Quick start

```bash
# Smoke (3 questions, balanced across buckets, low reasoning):
uv run python -m evals.run --reasoning low --limit 3

# Full 30 questions (~$1-3 at gpt-5 medium):
uv run python -m evals.run --reasoning medium

# Only rule_b cases (validate the conflict-citation behavior):
uv run python -m evals.run --reasoning medium --bucket rule_b

# Single question for debugging:
uv run python -m evals.run --reasoning medium --id q17
```

Each run writes three files into `evals/results/`:
- `<timestamp>_openai_<model>_<effort>[_<subset>].csv` — per-question DataFrame
- `<timestamp>_…json` — run metadata + aggregate metrics
- `<timestamp>_…md` — human-readable report (embeddable in README)

## Compare two runs

```bash
uv run python -m evals.compare \
  evals/results/2026-05-11_10-00-00_openai_gpt-5_low.csv \
  evals/results/2026-05-11_11-00-00_openai_gpt-5_medium.csv
```

Emits a markdown diff: aggregate deltas, per-bucket comparison, list of
questions that regressed (passed in A, failing in B) and improvements.

## Metrics

| Metric | Type | Source signal |
|---|---|---|
| **anchor_rate** | numeric 0-1 | `failure_reason is None` per citation |
| **citation_precision** | numeric 0-1 | cited passage_id ∈ `expected_passage_ids` |
| **refusal_correctness** | discrete | did the agent refuse iff golden expected it? |
| **general_knowledge_correctness** | discrete | Rule A: was general_knowledge_used flagged correctly? |
| **cost_usd** | numeric | sum of step token-usage costs |
| **tool_calls** | numeric | number of executed tool calls |
| **duration_ms** | numeric | wall-clock per question |

LLM-as-judge metrics (Faithfulness, AnswerRelevancy, etc.) are
deliberately out of scope. The `--with-judge` flag is reserved for
that future addition.

## Golden set

`evals/golden_set.yaml` — 30 hand-authored questions, distributed:

- 12 factual (with verified `expected_passage_ids` from the retrieval fixture)
- 4 rule_a (tangential mention; general_knowledge_used should fire)
- 4 rule_b (conflicting convictions; agent must cite both sides)
- 3 cross_lang (Spanish queries against PT/EN corpus)
- 4 out_of_scope (refusal expected; gen-know explicitly forbidden)
- 3 clarify (ambiguous; agent should ask for clarification)

PT 13 · EN 13 · ES 4.

Add new entries by appending to the YAML and re-running. IDs must be
unique; the loader rejects duplicates.

## CI

`pytest -m eval` runs only the `@pytest.mark.eval`-marked tests and
skips them silently when `OPENAI_API_KEY` isn't set. Default CI
(`pytest`) skips this layer entirely — it never burns tokens.
