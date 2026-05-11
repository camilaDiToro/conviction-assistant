# Retrieval scale

The v1 stack is **BM25 only** over ~30 markdown convictions, with unicode-fold + accent-strip + lowercase normalization. It works because the corpus is small and the target user is an internal Decade analyst who speaks the corpus vocabulary (PT/EN, tickers, acronyms like `FGC`, `CVM`, `IR`). On-vocabulary keyword queries are exactly where BM25 is strongest, and the citation verifier catches retrieval misses before they become hallucinations.

This doc covers the two ways that assumption breaks.

---

## If the corpus grows

BM25 stays useful (it's still best for exact-term matches: tickers, regulation numbers, acronyms), but the failure modes that surface as the corpus grows are different:

- **Hundreds of docs** — near-duplicates and topical neighbors start crowding the top-K. Add a **cross-encoder reranker** (`bge-reranker-v2-m3` or Cohere `rerank-multilingual-v3`) that re-scores candidates `(query, passage)` jointly. Adds ~50–150 ms per query.
- **Thousands of docs** — chunks pulled out of context lose meaning ("revenue grew 3%" — for which company?). Add **Anthropic-style Contextual Retrieval**: prepend a 50–100 token generated context summary to each chunk before indexing. Rebuild on doc changes.
- **Tens of thousands+** — single-Postgres becomes the bottleneck. Move lexical to OpenSearch / Elasticsearch / ParadeDB `pg_search`, dense to a dedicated vector store (Qdrant, Weaviate) or HNSW indexes in Postgres. Add metadata filtering (asset class, language) and shard by tenant if multi-tenant.

The agent loop, tool surface, citation contract, and verifier are unchanged at every step. Only the implementation of `search_convictions` grows.

---

## If users are not just internal Decade analysts

The internal-analyst assumption is what makes BM25-only viable. External users break it in one specific way: **they ask the same question with different surface forms.**

- A Spanish-speaking client asks `"tributación de CDB"`; the passage says `"tributação de CDB"` (PT). BM25 doesn't bridge `ó`↔`ã` or `ón`↔`ão`. **Misses.**
- An English-only user asks `"how is CDB taxed?"`; the passage is in Portuguese. Zero word overlap except `CDB`. **Misses.**
- A junior analyst paraphrases instead of using the regulatory term: `"qual o imposto sobre CDB?"` vs. passage `"a tributação dos CDBs segue..."`. BM25 hits but at middling rank.

The fix is to add a second retrieval path with a **multilingual embedding model** (OpenAI `text-embedding-3-large`, Cohere `embed-multilingual-v3`, or local `bge-m3`) over the same `passages` table — vectors stored in `pgvector` — and **fuse** the BM25 and dense ranked lists with Reciprocal Rank Fusion (k=60). BM25's exact-term wins (tickers, acronyms) are preserved; embeddings' cross-language and paraphrase wins are added; each method's worst failure mode is filtered out by the other.

Operational note: this adds an embedding pass over the corpus plus one embedding call per query.
