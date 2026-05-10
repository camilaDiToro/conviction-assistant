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
