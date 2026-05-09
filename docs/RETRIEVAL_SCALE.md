# Retrieval scale cheat-sheet

Why each corpus size implies a different retrieval stack. Short and simple.

## ~30–50 docs (current — what we're building for v1)

**Stack: BM25 only.** SQLite FTS5 or `rank_bm25` over passages.

- Why it works: keyword match is enough when there are only ~30 documents. The agent loop compensates for any retrieval miss by re-querying.
- Why nothing more is needed: embedding models, vector DBs, and rerankers add infrastructure (one-time embedding cost, index rebuilds, multilingual model selection, second model in the loop) that buys nothing measurable at this size.
- Cost: zero infra; one Python dependency.

## Hundreds (~100–500 docs)

**Stack: BM25 + dense embeddings, fused with RRF.** Add a multilingual embedding model (`bge-m3` for PT+EN); store vectors in SQLite or a small in-process library.

- Why BM25 alone starts to crack: more documents → more keyword collisions; queries phrased differently from the source ("CDB taxation" vs "tributação de CDB") need semantic matching.
- Why embeddings alone aren't enough: keyword search is still better for exact terms (ticker symbols, regulatory acronyms). Hybrid wins.
- Cost: one-time embedding pass over the corpus (~$1 per million tokens with a small model); ~50 MB of vectors; one extra dependency.

## Thousands (~1k–10k docs)

**Stack: BM25 + dense + cross-encoder reranker.** Optionally Anthropic-style **Contextual Retrieval** (prepend a generated 50–100 token context summary to each chunk before indexing).

- Why a reranker becomes necessary: top-K from hybrid search starts to include too many false positives at this scale. A cross-encoder (`bge-reranker-v2-m3`) re-scores the top-30 down to the top-8 with much better precision.
- Why Contextual Retrieval helps here: at this scale, chunks pulled out of context lose meaning ("revenue grew 3%" — for which company, which quarter?). The technique prepends per-chunk context to fix this. Reduces failed retrievals by 49% (or 67% with reranking) per Anthropic's benchmark.
- Cost: one-time per-chunk context generation (~$1 per million doc tokens with prompt caching); reranker adds ~100 ms per query.

## Tens of thousands and beyond

**Stack: real vector store + production retrieval pipeline.** Move off SQLite to something like pgvector, Qdrant, or Weaviate; introduce metadata filtering (asset class, date, language); consider sharding.

- Why now: in-process vector libraries struggle past tens of thousands of vectors. Production-grade stores give you metadata filtering, replication, and operational tools (snapshots, online updates).
- Why metadata filtering matters: the search should be able to scope to "convictions about Brazilian fixed income, updated in the last 12 months" without scanning everything.
- Cost: real infra to operate; not a v1 problem.

## Rule of thumb

| Corpus size | What changes | Who pays |
|---|---|---|
| ~30–50 | Nothing — BM25 is fine | Free |
| Hundreds | Add dense embeddings (hybrid) | One-time embedding cost |
| Thousands | Add a reranker; consider Contextual Retrieval | Per-query latency + one-time per-chunk context |
| Tens of thousands+ | Real vector store; metadata filtering | Operational complexity |

The agent loop, citation contract, and verifier in `ARCHITECTURES.md` stay identical at every scale. Only the *implementation of `search_convictions`* changes. That's the whole point of having retrieval behind a tool boundary.
