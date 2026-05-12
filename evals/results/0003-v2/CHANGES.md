# 0003-v2 — Changes vs 0003-v1

Baseline: `evals/results/0003-v1/` (same 6 questions on 4 models).
This iteration applies the 4 non-overfitting fixes surfaced by v1 and
re-runs the same questions on the two finalist configs (gpt-5.5 low,
gpt-5.4-mini low).

## 1. Golden set — q20 rewritten (rule_b)

**Why.** The v1 rule_b sample showed `conflict_disclosure = 0.000`
across all 4 models. Re-reading the corpus, the old q20 (prefixado
vs IPCA+ when Selic real stays high) is *conditional advice*, not a
literal conviction-level disagreement — under the question's premise,
both `tesouro_direto_estrategias_avancadas` and `ntnb_titulos_guia`
point toward IPCA+. Models correctly didn't manufacture a conflict.

**Change.** New q20 surfaces a real literal opposition:
NTN-B (sovereign, guaranteed real yield) vs debêntures incentivadas
(corporate credit, IPCA+ without IR, higher after-tax real yield) as
the right long-horizon real-return instrument.

## 2. Golden set — q24 re-bucketed (out_of_scope → rule_a)

**Why.** All 4 v1 models answered q24 with a `general_knowledge_section`
instead of refusing. They were right: the corpus does touch Lei 14.754
("rendimentos no exterior") which is the Brazilian side of the question,
so per the system prompt's `out_of_scope` rule the correct behavior IS
to cite the tangential Brazil-side passage and put the US-treaty
mechanics in `general_knowledge_section`. The golden set was wrong.

**Change.** `bucket: out_of_scope` → `bucket: rule_a`;
`expected_out_of_scope: true` → `expected_general_knowledge: true`;
`must_cite_at_least: 0` → `must_cite_at_least: 1`. Bucket distribution
updated to 12 factual / 5 rule_a / 4 rule_b / 3 cross_lang /
3 out_of_scope / 3 clarify.

**Principle.** Any investing question where the corpus tangentially
touches the topic is NOT out_of_scope — it's a Rule A case. The
out_of_scope bucket is reserved for non-investing topics and greetings.

## 3. System prompt — Rule A anti-duplication clause

**Why.** v1 showed a systematic leak on gpt-5.4-mini (both `low` and
`medium`): the model copies the entire `general_knowledge_section`
block, including the "Not from Decade convictions — general knowledge:"
heading, into the `answer` field. This violates the Rule A "never
interleave" intent even when `gk_section` itself is populated correctly.

**Change.** Added explicit clause to `app/agent/prompts/system.md`:

> No duplication across fields. A sentence (or paraphrase of it) that
> appears in `general_knowledge_section` MUST NOT also appear in
> `answer`. Each piece of general-knowledge content lives in exactly
> one place — the section. Do not echo, summarize, or restate gk
> content inside `answer`. If you find yourself writing the same
> thought in both fields, delete it from `answer`.

The prompt-hash changes automatically (`_prompt_version` in `evals/run.py`
content-hashes `system.md`).

## 4. Resolver — NFKC + smart-quote/dash/NBSP folding

**Why.** v1 had a steady trickle of `offset_not_found` failures on
gpt-5.4 and mini, mostly from typographic quotes/dashes/NBSP cosmetic
diffs between what the model copied and the DB-verbatim passage text.

**Change.** `app/agent/resolver/substring.py` now applies a
length-preserving 1:1 fold to both the citation quote and the passage
text before substring search:

- LEFT/RIGHT DOUBLE QUOTATION MARK, « », single quotes → `"` / `'`
- EN DASH, EM DASH, MINUS SIGN → `-`
- NO-BREAK SPACE, NARROW NBSP, THIN SPACE → ` `
- per-char NFKC where the result stays one codepoint

Length-preservation means normalized offsets equal original offsets —
no index map needed; the returned `(start, end)` still slices the
original passage. Multi-char NFKC decompositions (ligatures, fractions)
are intentionally left alone — better to miss the highlight than
return offsets that don't match the displayed passage.

Tests updated in `tests/agent/resolver/test_substring.py`: the old
"smart quotes do NOT normalize" design guard is replaced by two
positive cases (smart-quote + dash fold; NBSP fold).

## What did NOT change

- The agent loop, the tool dispatcher, the retrieval layer, the
  dedupe, the API contract — all untouched.
- Deterministic metrics in `evals/metrics.py` — untouched. The judge
  schema in `evals/judge/schema.py` — untouched.
- The other 5 rule_b notes (q17, q18, q19) — verified as real
  conviction disagreements; left as-is.

## Re-run plan

Same 6 questions (q04, q14, q20, q22, q24, q28) on:
- gpt-5.5 / low
- gpt-5.4-mini / low

Then `claude-opus-4-7` judge, then `_combined.md` per run, plus a
top-level comparison summary in this folder.

## Cross-version comparison contract

v1 vs v2 numbers are **only directly comparable on questions whose
bucket and golden expectations did not change** — i.e. q04, q14, q22,
q28. q20 changed question entirely; q24 changed bucket + expected
flags. For q20/q24, v2 is a fresh baseline.
