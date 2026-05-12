# Run group 0002 — what changed vs 0001

Runs in this folder were produced after the changes introduced on branch
`agent/conflict-fields`. They are NOT directly comparable to 0001 runs
without keeping these shifts in mind.

## Code changes between 0001 and 0002

### 1. Rule B is now a structural contract, not prose guidance

The 0001 runs showed `conflict_disclosure = 0.000` for both `gpt-5.5`
and `gpt-5.4` on the single `rule_b` question (`q17`). The judge's
reason was always the same:

> "agent presents a balanced synthesis but never uses an explicit
> disagreement marker"

The old prompt said *"State explicitly that the convictions disagree"*
but left the wording to the model, which preferred neutral framings
like "trade-off" or "tension".

**Fix:** Rule B is now enforced through the structured output schema.
`AnswerOutput` gained two fields:

- `conflict_detected: bool` — set true when two cited passages
  contradict each other on the user's topic.
- `conflict_statement: str | None` — required when the flag is true;
  must contain one of the literal phrases (per language):
  - PT: "as convicções divergem" / "as convicções discordam"
  - EN: "convictions disagree" / "the convictions conflict"
  - ES: "las convicciones difieren" / "las convicciones discrepan"

A `@model_validator` rejects inconsistent combinations (flag without
sentence, or sentence without flag). The fields propagate to
`ChatAnswerResponse`, the audit payload, and the `ConversationMessage`
reconstruction path, plus the frontend types.

### 2. Out-of-scope is about *investing topicality*, not corpus coverage

In 0001, `gpt-5.4` set `out_of_scope=true` on `q13` (Roth IRA) — a
legitimate investing question that the corpus does not cover.
`refusal_correctness` dropped to 0.750. The model conflated "the
corpus doesn't mention this" with "this is out of scope".

**Fix:** the prompt's *Out of scope* section now states explicitly
that `out_of_scope=true` applies **only** when the question is not
about investing (greetings, weather, cooking, sports, etc.). Investing
questions the corpus doesn't cover MUST fall back to Rule A:
search anyway, cite the most tangential conviction passage you can
find, and put the actual answer in `general_knowledge_section` with
`general_knowledge_used: true`. Refusing a real investment topic is
called out as a worse failure than a marked general-knowledge answer.

### 3. `citation_precision` no longer penalises extra citations

In 0001, the `gpt-5.5` run anchored 100% of its citations on `q01`
and `q21` but still scored `citation_precision=0.500` because it
emitted one anchored citation outside `expected_passage_ids`. The
judge inspected those citations and marked them legitimate — the
golden set was under-specified, not the agent over-citing.

**Fix:** `evals.metrics.citation_precision` now computes
`|matched ∩ expected| / |expected|`. Citations whose `passage_id` is
not in `expected_passage_ids` are treated as **neutral** — they do
not lower the score. The metric still drops when an expected id is
missing. The reason string surfaces both numbers, e.g.:

> "2/2 expected ids cited (1 extra cite, not penalised)"

Numerically this collapses to recall, but the lens is "did the agent
cover what we asked for, regardless of extras"; the column is kept
so downstream CSV/MD report readers don't break.

## How to read 0002 vs 0001

- **`conflict_disclosure` in 0002 reports** should be non-zero on
  `q17`-style buckets when the agent correctly surfaces a conflict.
  A zero now signals a real failure (the model didn't even set the
  flag), not a wording style mismatch.
- **`refusal_correctness` regressions on rule_a buckets** in 0001
  should resolve in 0002 — the model should attempt a general-
  knowledge answer instead of refusing.
- **`citation_precision` scores in 0002 reports are not comparable**
  to 0001 line-for-line; a 0002 score of 1.0 includes cases that 0001
  would have scored 0.500. Trend on it only within a group.

## How to make a 0002 run

```pwsh
uv run python -m evals.run --out evals/results/0002 --reasoning low --limit 4
```

The runner writes the same `.csv` / `.json` / `.md` / `_combined.md`
/ `_judge.jsonl` / `_traces.jsonl` artefacts as before — only the
output directory differs.
