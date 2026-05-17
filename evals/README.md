# Eval suite

Hand-authored golden set + deterministic metrics + runner + comparator.
The headline metric is **anchor rate** — what fraction of cited quotes
resolved to an offset region in the cited passage.

## Quick start

```bash
# Smoke (3 questions, balanced across buckets, low reasoning):
uv run python -m evals.run --reasoning low --limit 3

# Full golden set (~$1-3 at gpt-5 medium):
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

## Deterministic metrics

| Metric | Type | Source signal |
|---|---|---|
| **anchor_rate** | numeric 0-1 | `failure_reason is None` per citation |
| **citation_recall** | numeric 0-1 | expected passage_id is in cited set |
| **refusal_correctness** | discrete | agent refused iff `expected_out_of_scope` (now two-direction — false refusals on in-scope Qs also penalised) |
| **general_knowledge_correctness** | discrete | Rule A: was `general_knowledge_used` flagged correctly? |
| **clarify_correctness** | discrete | agent asked a clarifying question iff `bucket=="clarify"` |
| **meets_min_citations** | discrete | distinct citations ≥ `must_cite_at_least` |
| **conflict_min_citations** | discrete | Rule B precondition: ≥ 2 distinct citations when `expected_conflict_mention=true` |
| **language_match** | discrete | answer (or clarifying question) is in the user's language |
| **prompt_tokens / completion_tokens / cached_tokens / reasoning_tokens** | numeric | raw provider token counters summed across LLM steps |
| **tool_calls** | numeric | number of executed tool calls |
| **duration_ms** | numeric | wall-clock per question |

## LLM-as-judge layer

Five semantic metrics live in `evals/judge/`. The judge runs
**manually from a code assistant**, not as a subprocess or CLI command:
there is no code path that calls a judge model. Read
`evals/judge/prompt.md`, apply it to each record of the `_traces.jsonl`
produced by the deterministic run, and write a JSONL of `JudgeResult`
records validated against `evals/judge/schema.py`.

| Judge metric | Type | What it checks |
|---|---|---|
| **faithfulness** | numeric 0-1 | fraction of `answer` sentences entailed by the cited passages |
| **answer_relevancy** | discrete | answer addresses the user's question (relevant / partial / off_topic) |
| **rule_a_purity** | discrete | `answer` is free of general-knowledge content (clean / leaked) |
| **citation_attribution** | numeric 0-1 | each `[N]` marker maps to a passage that supports the preceding claim |
| **completeness** | discrete | answer covers the substantive points in the cited material (complete / partial / shallow) |

Combined report:

```bash
uv run python -m evals.judge.aggregate \
    evals/results/<ts>_..._.csv \
    evals/results/<ts>_..._judge.jsonl \
    --out evals/results/<ts>_..._combined.md
```

The aggregator refuses to merge a judge JSONL whose records carry
inconsistent `(judge_model, judge_prompt_hash)` — two judge runs are
only comparable when both signatures match.

## Golden set

`evals/golden_set.yaml` — 34 hand-authored questions, distributed:

- 18 factual (incl. 2 multiturn; verified `expected_passage_ids` from the retrieval fixture)
- 5 rule_a (tangential mention; general_knowledge_used should fire)
- 3 rule_b (conflicting convictions; agent must cite both sides and emit conflict_detected=true)
- 3 cross_lang (Spanish queries against PT/EN corpus)
- 2 out_of_scope (refusal expected; gen-know explicitly forbidden)
- 3 clarify (ambiguous; agent should ask for clarification)

PT 15 · EN 15 · ES 4.

Add new entries by appending to the YAML and re-running. IDs must be
unique; the loader rejects duplicates.

## CI

`pytest -m eval` runs only the `@pytest.mark.eval`-marked tests and
skips them silently when `OPENAI_API_KEY` isn't set. Default CI
(`pytest`) skips this layer entirely — it never burns tokens.
