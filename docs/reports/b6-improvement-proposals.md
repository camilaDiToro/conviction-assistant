# B6 — improvement proposals (NOT implemented in v1)

**Companion to:** `docs/reports/b6-eval-results.md` (BM25 hits 69%) and `docs/reports/b6-eval-methodology.md`.
**Status:** none of the below have been built. This document is the design space for closing the eval gap.

> **Planned next step (B6.5): proposal 1 — hybrid BM25 + multilingual dense embeddings + RRF.** Decided 2026-05-10. To be implemented as a separate step after B6 ships. Implementation outline below under proposal 1.
>
> Proposals 2–6 remain documented but **deprioritized**: their expected lift is small relative to hybrid, or they only become relevant at much larger corpus sizes. They stay on file so a future reviewer can see the design space we considered.

The proposals are ordered by expected ROI for this 30-doc corpus, *not* by how interesting the technique is. At larger corpus sizes the order changes — see `docs/RETRIEVAL_SCALE.md`.

---

## Proposal 1 — Hybrid retrieval: BM25 + dense embeddings + RRF  *(planned for B6.5)*

**Expected gain:** the largest single lift. Cross_lang would go from 0/5 toward 3–5/5; topic from 5/8 toward 7–8/8; the `pgbl-vgbl` literal failure resolves because dense matches the heading semantically. Likely overall primary recall@5 ≥ 90%, weighted score ≥ 0.92.

**Why it works for our failures:**
- `dolarizacion` ↔ `dollarization`: dense embeddings put cognates in the same neighborhood.
- `fondos` ↔ `fundos`: same idea, sub-word semantic match.
- `pgbl-vgbl-diferenca-pt-literal`: the expected heading "Diferença Fundamental: A Mecânica Fiscal" is semantically *about* PGBL/VGBL fiscal mechanics; dense ranks it higher than length-biased BM25.
- `juros sobre capital próprio` paraphrase: dense handles the synonym set.

**Design:**
- Provider: reuse `EmbeddingProvider` (already implemented in B4). Default model: `text-embedding-3-large` (3072d, multilingual). Alternative: `bge-m3` (1024d) if PT/EN cross-language is shaky and we want a model trained more heavily on multilingual.
- Storage: at 30 passages × 3072 dims × 4 bytes ≈ 360 KB, an in-memory numpy float32 matrix is fine. No vector DB. Persist alongside BM25 index in lifespan.
- Fusion: Reciprocal Rank Fusion (RRF), `k=60`. Standard IR fusion; no learned weights needed.
- Lifecycle: at startup and on ingest, embed every passage in one batch; rebuild both indexes together.
- Cost (one-time per ingest, then read-only): 30 passages × ~200 tokens average × $0.13/M tokens = roughly $0.001 per ingest. Negligible.
- Latency: query embed (~50–150 ms first call) + BM25 (~3 ms) + cosine over 30 vecs (<1 ms) + RRF (<1 ms). Worst case ~200 ms p95 — still well under any reasonable chat budget.

**Effort:** ~2–3 hours. Most of it is RRF + lifecycle; the embedding provider already works.

**ROADMAP placement:** B6.5 — to be added as a discrete step after B6 ships. The repository contract in `app/services/search.py` is the swap point — `BM25Index` becomes one of two retrievers wrapped by a `HybridIndex`; the `search_convictions` tool surface does not change.

**Implementation outline (for the future B6.5 PR):**
1. New `DenseIndex` class in `app/services/search.py` — embeds passages at `build()`, holds a numpy float32 matrix, returns top-k by cosine similarity at `search()`.
2. New `HybridIndex` class — owns one `BM25Index` and one `DenseIndex`; at `search()`, runs both, fuses ranks via RRF (k=60), returns the merged top-k.
3. `ToolContext.search_index` becomes `HybridIndex` (interface stays the same — `search(query, k) -> list[(Passage, score)]`).
4. Tests:
   - Unit: mock `EmbeddingProvider` (use `StubEmbedder` from B4) so CI never burns tokens.
   - Acceptance: re-run `tests/tools/test_search_convictions.py::test_retrieval_golden` against `text-embedding-3-large` once, gated on `OPENAI_API_KEY`. Per-bucket floors tightened (e.g., topic ≥ 80%, cross_lang ≥ 60%).
5. Write `docs/reports/b6.5-results.md` showing before/after — both primary and weighted scores so the lift is visible across the secondary-id cases.

**Cost of *not* doing it:** the 0% cross_lang result effectively means Spanish users can't find PT/EN content via search. PT-only / EN-only users are mostly fine — but the verifier (B7) will protect them from any hallucinated citation regardless.

### Supporting research — why the multilingual hybrid shape is the right one

The hybrid + multilingual + reranker design above isn't an off-the-shelf textbook recipe; each component is grounded in a specific paper or production result. The seven references below are the ones a reviewer would expect us to have read before promoting B6.5.

| Idea | Why it matters for our PT + EN (+ ES queries) corpus | Reference |
|---|---|---|
| **Multilingual retrieval is not automatically solved by embeddings — BM25 can still be very strong.** | Validates the v1 BM25-only baseline. For exact terms, entity names, ticker codes, table labels, and metric names, lexical search remains competitive; you don't *start* with embeddings, you *add* them. | **Mr. TyDi** — multilingual dense retrieval benchmark; dense was weaker than BM25 alone on most languages, and shone only when combined as sparse+dense. [arXiv 2108.08787](https://arxiv.org/abs/2108.08787) |
| **Use hybrid retrieval: BM25 + multilingual dense.** | The safest base architecture for mixed-language corpora. BM25 catches exact matches; dense catches cross-lingual paraphrase. This is exactly Proposal 1 above. | **Mr. TyDi** — same paper, supports sparse+dense hybrid as the consistently better baseline. [arXiv 2108.08787](https://arxiv.org/abs/2108.08787) |
| **Document translation can outperform query translation.** | If hybrid alone doesn't close the cross_lang gap, the next move is to index translated chunks (e.g. EN translations of PT passages) rather than translating queries on the fly. Document-side translation has the empirical edge. | **CLIRudit (Cross-Lingual IR of Scientific Documents)** — compares query translation vs document translation vs dense vs sparse; document translation generally wins. [ACL 2025.mrl-main.16](https://aclanthology.org/2025.mrl-main.16.pdf) |
| **Evaluate cross-lingual RAG separately from multilingual retrieval.** | Retrieval can succeed while generation still fails — the model may struggle to answer in the user's language given evidence in another. Our eval suite (B10) needs explicit PT-query→EN-doc and ES-query→PT-doc cases scored end-to-end, not just at retrieval. | **XRAG** — benchmark for cross-lingual RAG where user language ≠ retrieved-doc language. [arXiv 2505.10089](https://arxiv.org/abs/2505.10089) |
| **A multilingual retrieval benchmark mindset is valuable, but don't copy results blindly.** | MIRACL is the standard bar but is mostly *monolingual* (query and corpus same language). It doesn't directly test our cross_lang failure mode; XRAG and CLIRudit are the better proxies. | **MIRACL** — 18-language retrieval benchmark, 78k queries, 726k judgments. [TACL 2023.tacl-1.63](https://aclanthology.org/2023.tacl-1.63/) |
| **BGE-M3 is a strong open-source candidate for the embedding side.** | If we want to drop the OpenAI dependency on the dense path (or want one model that handles dense + sparse + multi-vector), BGE-M3 supports 100+ languages in a single checkpoint. Listed as the alternative to `text-embedding-3-large` in Proposal 1 above. | **BGE-M3** — multi-lingual, multi-functionality, multi-granularity embeddings via self-knowledge distillation. [arXiv 2402.03216](https://arxiv.org/abs/2402.03216) |
| **A multilingual reranker is the precision lift on top of hybrid (Proposal 5).** | Once hybrid puts the right passage in the top-N, a cross-encoder reranker promotes it to top-1. Must be multilingual to handle EN + PT (+ ES) without language-specific routing. | **Cohere Rerank 4.0** — single multilingual reranker trained on 100+ languages. [Cohere docs](https://docs.cohere.com/docs/rerank-overview) |

**One additional empirical anchor — BM25 vs dense on financial-domain text.** A 2025 benchmark on financial documents found that **BM25 outperforms `text-embedding-3-large` on every metric except Recall@20**, attributed to the precision of domain terminology (ticker codes, fund names, regulatory references, fiscal mechanics). This is exactly our domain. It explains why BM25 hits 93.8% on the literal bucket here — and also why the hybrid lift on Proposal 1 is *primarily* about cross_lang and topic recall, not about replacing BM25 wholesale on literal queries. The hybrid argument is "keep BM25's wins, add dense for the failure modes," not "embeddings are better."

- **From BM25 to Corrective RAG: Benchmarking Retrieval Strategies (arXiv 2025).** [arXiv 2604.01733](https://arxiv.org/abs/2604.01733). Single most relevant paper for justifying *both* the v1 BM25-only ship AND the planned hybrid promotion — same paper covers the whole arc.

**What this research changes about the implementation outline above:**

1. Pin **`bge-m3`** as the dense embedder for B6.5 (not `text-embedding-3-large`) — the multilingual-distilled training is a better fit for PT/EN/ES paraphrase than OpenAI's general embedder, and it removes a provider dependency from the retrieval path. Keep `text-embedding-3-large` as the documented alternative.
2. Add an **explicit XRAG-style cross-lingual eval slice** to B10 (PT-query→EN-doc, ES-query→PT-doc, EN-query→PT-doc) so we can detect the case where retrieval works but generation regresses.
3. **Defer Cohere Rerank to Proposal 5** as currently scoped — rerankers earn their keep only after hybrid puts good candidates in the top-30. The Cohere reference is here to pre-commit the multilingual choice if/when we promote.

## Proposal 2 — Tune BM25: k1 / b parameters and BM25L variant

**Expected gain:** small. Maybe recover `pgbl-vgbl-diferenca-pt-literal` and 1 topic case. Cross_lang stays at 0.

**Why it might help (some cases):**
- `pgbl-vgbl-diferenca-pt-literal` lost to a longer passage in another doc. Lowering `b` (length normalization, default 0.75) penalizes long docs less but penalizes short relevant passages less too — net effect uncertain.
- BM25L is a length-aware variant designed for *short* documents to avoid over-penalizing short relevant ones. Theoretically helpful here.

**Why it won't help (most cases):**
- Cross_lang failures are about vocabulary, not length. Tuning BM25 doesn't add a token bridge between `fondos` and `fundos`.
- Topic failures (`jcp`, `dividendo-obrigatorio`) are about paraphrase. BM25 has no notion of synonyms.

**Design:**
- bm25s exposes `BM25(method="lucene"|"robertson"|"atire"|"bm25l"|"bm25+", k1=…, b=…)`.
- Grid search over the fixture: `k1 ∈ {0.9, 1.2, 1.5, 1.8}`, `b ∈ {0.25, 0.5, 0.75}`, `method ∈ {lucene, bm25l}`.
- Risk: tuning to the fixture (overfitting). The fixture is small (29 cases); a 2–3% gain is within noise.

**Effort:** ~1 hour. Cheap to try.

**Recommendation:** worth a brief experiment to pin defaults, but not a substitute for hybrid retrieval. Document the chosen `(k1, b, method)` in a note; don't ship a tuning loop in production.

## Proposal 3 — Query expansion at search time

**Expected gain:** modest for ES↔PT cross_lang. Could lift 1–3 cross_lang cases.

**Idea:** at query time, route the query through a lightweight rewrite that adds known cognates (`fondos → fundos`, `dolarización → dolarização`, `impuesto → tributação`). Could be:
- A static dictionary (most maintainable; brittle).
- An LLM-based rewrite call before BM25 (expensive, defeats the "no LLM in retrieval" principle).
- A multilingual stemmer / fuzzy matching at indexing time (e.g., `n-gram` overlap or `SymSpell`).

**Why it has limits:**
- Cognates only cover surface variations. `succession` → `sucessão` works; `small caps` → `acciones de pequeña capitalización` requires real translation.
- A static dict has to be maintained per query language pair; it's the kind of feature that quietly grows old.
- An LLM rewrite call adds the very dependency the retrieval design tries to avoid.

**Effort:** ~2 hours for a static dict; ~1 hour for character-n-gram fallback indexing.

**Recommendation:** lower priority than hybrid retrieval. Hybrid solves the same problem with a single principled mechanism.

## Proposal 4 — Per-language indexes

**Idea:** maintain three BM25 indexes (PT, EN, ES) using `bm25s.tokenize(stopwords=lang, stemmer=PyStemmer(lang))`. At query time, detect language, hit the matching index, *also* hit the others as a fallback.

**Expected gain:** small for monolingual queries (stemming helps a bit). Negative for cross_lang (still no bridge).

**Why I rejected this for v1:** the user explicitly preferred the simple-tokenization approach ("if bm25 does not work it should be upgraded to the mixture with vectors"). Per-language indexes are extra complexity in the same direction without solving cross_lang.

**Recommendation:** skip. If we want per-language behavior, do hybrid first; per-language stemming becomes irrelevant once dense retrieval handles paraphrase.

## Proposal 5 — Cross-encoder reranker (e.g. mxbai-rerank, bge-reranker)

**Idea:** retrieve top-30 with BM25 (or hybrid), then rerank with a cross-encoder that scores each (query, passage) pair.

**Expected gain:** the largest *precision* lift but only after retrieval candidates are good. A reranker does nothing if the right passage isn't in the top-30 BM25 list — and right now several of our failures (cross_lang especially) aren't in BM25's top-30 at all.

**Recommendation:** wait. Cross-encoders shine at hundreds-of-passages scale or after hybrid is in place. At 30 docs, hybrid alone closes the gap.

## Proposal 6 — Anthropic-style Contextual Retrieval

**Idea:** at ingest time, each passage gets a 1–2-line LLM-generated context summary prepended. The augmented passage is then indexed (BM25 + dense). Anthropic showed substantial gains on RAG benchmarks.

**Where it fits:** at hundreds-of-docs scale where passages are tightly bounded chunks losing context. Our passages are full document sections (`## Heading + body`) and already carry context.

**Effort:** higher (~1 day): one-time LLM call per passage at ingest, plus the prompt design.

**Recommendation:** only relevant after we cross ~100 docs *and* hybrid retrieval still has gaps. Out of scope for the foreseeable future.

---

## Summary table

| Proposal                     | Effort | Expected lift on overall recall@5 | Notes |
|------------------------------|--------|-----------------------------------|-------|
| 1. Hybrid (BM25 + dense + RRF) | 2–3 h  | +20–25 pp (69% → ~90%)            | The right answer at this scale. |
| 2. BM25 tuning (k1/b/BM25L)    | 1 h    | +0–5 pp                           | Cheap experiment; not a replacement. |
| 3. Query expansion             | 2 h    | +5–10 pp on cross_lang            | Maintenance overhead; hybrid subsumes. |
| 4. Per-language indexes        | 3 h    | +0–5 pp                           | Skip — hybrid is strictly better. |
| 5. Cross-encoder reranker      | 1–2 d  | needs hybrid first                | Premature without good candidates. |
| 6. Contextual Retrieval        | 1+ d   | minimal at this scale             | Premature; for >100 docs. |

## Recommendation

If we promote anything: **proposal 1 (hybrid retrieval) as a single B6.5 step**, with proposal 2 as a 30-min sanity-check before kicking off proposal 1. Skip the rest until a real bottleneck appears.

If we do nothing: ship BM25 v1, document this report in the README's "deliberately simplified" section, and let the verifier (B7) protect the user from any retrieval-induced hallucination — the agent simply won't be able to fabricate a citation that BM25 missed, because the verifier substring-checks every quote.
