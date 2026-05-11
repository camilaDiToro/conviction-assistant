# Eval cross-model comparison — summary

**Date**: 2026-05-11
**Prompt version**: `0a46a372` (after Rule A tightening + the contiguous-quote clarification)
**Branch**: `b10-evals-and-config-ui`
**Subset**: 3 questions (q01 factual PT, q13 rule_a PT, q17 rule_b PT)

## What I ran

5 configurations × 3 questions, on the same `system.md` and same golden set:

| Config | Adapter | Anchor | Citation prec | Gen-know | Cost (3q) | Avg dur | Tool calls |
|---|---|---|---|---|---|---|---|
| **gpt-5.5 / low**          | `/v1/responses`    | **1.000** | 0.000 | 2/3 | $0.085 | 33s | 3.0 |
| **gpt-5.5 / medium**       | `/v1/responses`    | **1.000** | 0.000 | 2/3 | $0.122 | 42s | 3.3 |
| **gpt-5.4-mini / low**     | `/v1/responses`    | 0.778     | 0.000 | 2/3 | **$0.015** | **13s** | 3.0 |
| **gpt-4.1 / —** (no reas.) | `/v1/chat`         | **1.000** | **0.500** | 2/3 | $0.098 | 30s | 2.7 |
| gpt-5 / low (legacy)       | `/v1/chat`         | 0.667     | 0.333 | 2/3 | $0.111 | 86s | 3.7 |

Token totals on the 4 modern configs (3-question run): 65–75k prompt, 3–6k completion, 0–1.2k reasoning.

## OpenAI model lineup as of May 2026

| Family | Models that exist | Endpoint required |
|---|---|---|
| **gpt-5.5** (flagship, April 2026) | `gpt-5.5`, `gpt-5.5-pro` — **NO `gpt-5.5-mini`** (verified 400 model_not_found) | `/v1/responses` |
| **gpt-5.4** (cost tier of the .5 generation) | `gpt-5.4-mini`, `gpt-5.4-nano` | `/v1/responses` |
| gpt-5.1 | `gpt-5.1` | `/v1/chat/completions` |
| gpt-5 (legacy, Aug 2025) | `gpt-5`, `gpt-5-mini`, `gpt-5-nano` | `/v1/chat/completions` |
| gpt-4.1 (modern non-reasoning) | `gpt-4.1`, `gpt-4.1-mini`, `gpt-4.1-nano` | `/v1/chat/completions` |
| gpt-4o (legacy non-reasoning) | `gpt-4o`, `gpt-4o-mini` | `/v1/chat/completions` |

OpenAI advances the flagship and the cost-tier on different cadences — the small sibling of `gpt-5.5` is named `gpt-5.4-mini`, not `gpt-5.5-mini`. Easy to trip over.

## Headline findings

### 1. The Responses API migration moved the needle — anchor 0.667 → 1.000

Same prompt, same golden, same questions: `gpt-5` (legacy, chat completions) anchored 0.667; `gpt-5.5` (modern, Responses API) anchored **1.000**. The new flagship copies verbatim more faithfully and produces fewer paraphrased citations.

The migration was non-trivial (different input/tools/output wire shape) but the provider abstraction held: agent loop, tools, resolver, and tests didn't change. Single `_requires_responses_api(model)` check in the factory routes per model.

### 2. Medium reasoning ≠ better answers on this task

`gpt-5.5 / medium` produces identical outputs to `gpt-5.5 / low` on these 3 questions. Same anchor rate, same citations chosen, same gen-know decisions. Medium just consumes 7× more reasoning tokens (174 → 1246) and costs 44% more.

For this corpus, citation contract, and loop bound, low is the right default. Production should set `AGENT_REASONING_EFFORT=low`.

### 3. gpt-4.1 without any reasoning ties gpt-5.5

`gpt-4.1` with **0 reasoning tokens** hit anchor 1.000 and was the only modern config that scored citation_precision > 0 on q01. It also used the fewest tool calls (2.7 vs 3.0–3.3) and finished in 30s.

At this scale (30-doc corpus, max-5 tool loop, strict JSON schema, verbatim-only citations), most of the heavy lifting is in the prompt + tool dispatch + schema, not in reasoning tokens. Reasoning is paying for synthesis quality, not for the citation contract. **Re-evaluate with the full 30-question golden set before locking in gpt-5.5 as the default.**

### 4. gpt-5.4-mini is the cheap fast option — with one known weakness

5–7× cheaper than gpt-5.5 / gpt-4.1, 2–3× faster (~13s). But anchor drops on rule_a (q13: 0.33 — only 1 of 3 citations anchored). Acceptable for bulk-query / batch-ingest paths; not safe as the only model for analyst-facing chat.

---

## Where each problem actually lives — root-cause analysis after going to the corpus

For each issue I went back to the corpus and to the BM25 retriever to localise the bug, rather than assuming.

### A. `citation_precision = 0.000` on q01 across all gpt-5.x configs

**What the metric saw**: every gpt-5.x config cited `guia_completo_tributacao_investimentos#3-renda-fixa-cdb-lc-lci-lca-debentures-e-outros` and `tributacao_investimentos#3-renda-fixa-cdbs-...`. The golden expects only `cdbs_quick_guide#tributacao-tabela-regressiva`.

**What I checked in the corpus**:
- `cdbs_quick_guide.md` line 56 has a section `## Tributação: Tabela Regressiva` covering CDB taxation. ✓
- `guia_completo_tributacao_investimentos.md` line 79 has section `## 3. Renda Fixa: CDB, LC, LCI, LCA, Debêntures e Outros` and `### 3.1 CDB e LC — Tributação Padrão` line 81. Also legitimately about CDB taxation, with *more detail*.

So both passages cover the topic; the model citing the more detailed one is not wrong.

**What I checked in the retriever**: ran BM25 with the query `"tributacao CDB tabela regressiva"`:

```
TOP 1: cdbs_quick_guide#cdb-vs-tesouro-selic                   score=7.88
TOP 2: guia_completo#3-renda-fixa-cdb-lc-lci-lca-debentures…   score=7.12
TOP 3: guia_completo#1-principios-gerais-da-tributacao…        score=6.24
TOP 4: pgbl_vgbl#tabelas-de-tributacao-progressiva-vs-regress. score=5.91
TOP 5: multimercado#4-tratamento-tributario                    score=5.43
```

**The expected passage `cdbs_quick_guide#tributacao-tabela-regressiva` is NOT in the top 5.** BM25 ranks the "CDB vs Tesouro Selic" section higher inside the same doc, even though "Tributação: Tabela Regressiva" is the heading that literally matches the query terms. Likely because:
- The Tesouro-Selic section is longer and repeats "CDB" multiple times.
- The dedicated tax section is short (`## Tributação: Tabela Regressiva` + a few bullets) so its IDF-weighted term frequency loses.

**Where the problem really is**: **two layers, both real.**

1. **The retriever underweights short well-named passages.** Plain BM25 doesn't reward heading-term matches over body-term frequency. The roadmap's B6 level-up (BM25 + multilingual embeddings + RRF, behind a flag) would likely fix this — embedding similarity gives equal weight to a short, dense, on-topic passage and a long verbose one. Until then, the symptom is that q01-style "narrow factual" questions get noisy retrievals.
2. **The golden's `expected_passage_ids` is too narrow.** Even with the current BM25, multiple cited passages are correct answers. Strict-set match is harsh.

**Recommended fix**:
1. (Cheap) Widen `expected_passage_ids` on q01 to include `guia_completo_tributacao_investimentos#3-1-cdb-e-lc-tributacao-padrao` and `guia_completo_tributacao_investimentos#3-renda-fixa-cdb-lc-lci-lca-debentures-e-outros`. Document in the golden YAML that the metric is "at least one match counts".
2. (Real fix) Move to a hybrid retriever (B6 level-up) so the literal section-heading match wins. Eval-driven — only worth doing if other questions show the same retrieval shadowing.

### B. q13 `gen_knowledge=incorrect` on every model

**What the metric saw**: every model cited PGBL/VGBL passages and answered with `general_knowledge_used=false`. The golden expects `true`.

**What I checked in the corpus**:
- The corpus has **no dedicated life-insurance document**. `grep -l "seguro de vida"` returns only `pgbl_vgbl_comparacao.md`.
- The only literal mention of "seguro de vida" is on line 140: *"Por ser classificado como seguro, o VGBL é declarado na ficha de Bens e Direitos com o código específico de seguro de vida."* That is a **tax-form classification statement**, not a discussion of life-insurance-as-an-instrument.
- PGBL/VGBL `#planejamento-sucessorio-e-beneficiarios` (line 144) is rich on the topic: avoids inventário, named beneficiaries, compared to holdings/testamentos.

So when the user asks "Como devo estruturar **seguros de vida** junto à minha carteira para eficiência sucessória?", the corpus says nothing about traditional term/whole-life insurance products — it only has PGBL/VGBL, which:
- Sit in the previdência category, not the seguros category, despite the IR-form classification.
- Cover the *outcome* (succession without inventário) but via a different vehicle than the user asked about.

**What I checked in the retriever**: BM25 returns the right PGBL/VGBL passages with high scores (`#planejamento-sucessorio-e-beneficiarios` score 5.18). Search is fine.

**Where the problem really is**: **the model, not the golden, and not the retriever.**

The model is doing exactly what Rule A's first bullet says: "Always prefer a real conviction reference, even if it mentions the topic only tangentially". But it then *fails* the rest of Rule A: it doesn't notice that the user asked about life insurance, the corpus has PGBL/VGBL, and **bridging from "life insurance" to "PGBL/VGBL" is itself synthesis-beyond-citation**. None of the cited passages say "PGBL/VGBL is a substitute for life insurance"; the model is supplying that connection.

I tightened the prompt during this run to flag synthesis-beyond-citation. It didn't catch this case. Why?

- The cited passages literally talk about PGBL/VGBL avoiding inventário. The model treats its answer as "restating the cited passages".
- The mismatch is at the **question reframe** level: the user's "life insurance" → the model's "PGBL/VGBL". That happens before any sentence-by-sentence check.

**Recommended fix**:
1. Strengthen Rule A specifically for "the asked-instrument vs the cited-instrument" mismatch. New bullet to add to the prompt: *"If the user names a specific instrument (e.g. 'seguros de vida', 'crypto staking', 'estate trust') and your cited passages describe a **different** instrument that happens to serve the same goal, you are substituting — set `general_knowledge_used: true` and explain the substitution in `general_knowledge_section`."* Test this in a follow-up run.
2. (Alternative) Replace q13 with a cleaner rule_a question — one where the corpus simply doesn't have a tangential bridge. That removes the ambiguity but loses a real test case for substitution-style Rule A failures.

I'd take option 1. Substitution is a real failure mode and worth keeping in the eval.

### C. Medium reasoning shows no gain over low

**What I checked**: 7× more reasoning tokens (174 → 1246), same answers across all 3 questions.

**Where the problem is (if any)**: nowhere — it's a finding. At this corpus size and loop bound, the task is dominated by tool dispatch + verbatim copying. Reasoning doesn't change *which* passage to cite or *what* substring to quote.

**Recommended fix**: change `settings.agent_reasoning_effort` default from `medium` to `low`. Document the finding so it doesn't get reverted.

### D. gpt-5.4-mini drops q13 anchor to 0.333

**What I checked**: q13 produced 3 citations; 1 anchored. Looking at the trace, the 2 non-anchoring quotes were *almost* substrings but had small substitutions (different punctuation, joined word breaks). Standard sub-flagship-model verbatim drift.

**Where the problem is**: **model capacity**. The smaller model is less faithful to verbatim copying under PT-text + complex synthesis. q01 (simpler factual) and q17 (rule_b — clearer conflict) anchored fine.

**Recommended fix**: keep gpt-5.4-mini in the allowed list but never as the default. Document as "cheap-batch tier — accepts some anchor drift on rule_a-style multi-passage synthesis". Could be the default for an explicit `/batch` endpoint or for ingestion-time enrichment.

### E. Cost = $0 in the report for gpt-4.1 / gpt-4o / gpt-5.5 / gpt-5.4-mini

**What I checked**: `compute_call_cost_usd` raises `ProviderError("no pricing entry for model …")` because `_model_prices.json` only had `gpt-5` and `gpt-5-mini`. The eval runner suppresses that exception so one missing price doesn't kill the run, defaulting silently to $0.

**Where the problem is**: **the pricing JSON was stale**, and the eval runner's exception suppression hides the cause.

**Recommended fix**:
1. Added approximate price entries for gpt-5.5 / gpt-5.4-mini / gpt-5.1 / gpt-4.1 / gpt-4o; gpt-5.5 and gpt-5.4-mini carry `"_note": "approximate — confirm against live OpenAI pricing"`. Retroactive costs in the table above were recomputed off the trace token counts after this update.
2. Replace `suppress(Exception)` in `evals/run.py` with a warning that names the missing model — silent $0 is worse than a visible warning.

### F. q17 took ~150 s on gpt-5 / low (legacy) but only ~40 s on gpt-5.5 / low

**What I checked**: same prompt, same retrieval, same tools. Difference is the model.

**Where the problem is**: same `/v1/chat/completions` adapter, but gpt-5 (legacy) spent more wall-time inside the final synthesis call. Likely a server-side latency change between the August-2025 and April-2026 generations. Not actionable on our side.

**Recommended fix**: none — this resolves itself when we move the default to gpt-5.5.

---

## What should change in the project (concrete TODO)

1. **Default settings**: `OPENAI_MODEL=gpt-5.5`, `AGENT_REASONING_EFFORT=low`. (env already updated; `settings.py` still has `medium` as the default — change it.)
2. **Golden patches**: widen `q01.expected_passage_ids`; either rewrite q13 to test substitution-style Rule A or strengthen Rule A in the prompt with the substitution clause (recommended: prompt strengthening).
3. **Pricing**: confirm gpt-5.5 / gpt-5.4-mini approximate prices against the OpenAI billing page.
4. **Eval runner**: surface missing-pricing as a warning, not silent $0.
5. **Retrieval level-up gating**: q01 retrieval bias is a documented motivator for B6 (hybrid BM25+dense+RRF). Don't take it now, but keep it in mind when designing the eval-driven gate for B6.
6. **Re-run with 30 questions** comparing gpt-5.5 / low vs gpt-4.1: if gpt-4.1 stays competitive, it's the production default (cheaper, no reasoning surface to tune, identical anchor on this sample).

## Things that did not need fixing

- Agent loop, tools, resolver, audit, dedupe — untouched by the model swap.
- Frontend — already model-agnostic via `/api/config` + overrides.
- Citation contract / output schema — verbatim quote → offset resolver works identically across all 4 modern models.

The provider abstraction earned its keep: a flagship-model migration that required swapping the wire protocol (`chat.completions` → `responses`) cost one new adapter class + one factory branch. Nothing above the protocol moved.
