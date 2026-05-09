# Retrieval scale cheat-sheet

Why each corpus size implies a different retrieval stack — and why the v1 baseline already has to be **hybrid + multilingual**, not BM25-only.

The corpus is mixed Portuguese / English; queries are PT / EN / Spanish (per `ASSUMPTIONS.md` § "Languages"). A bag-of-words index alone can't bridge "CDB taxation" (EN query) → "tributação de CDB" (PT passage). So the v1 tier already needs semantic retrieval.

---

## v1 — ~30–50 docs (current target)

**Stack: hybrid BM25 + multilingual dense embeddings, fused with Reciprocal Rank Fusion.**

- **BM25-style lexical** via **Postgres FTS** (`tsvector` + `to_tsvector` + `ts_rank_cd`, with the `unaccent` extension for PT/EN/ES coverage) — handles exact-term matches (ticker symbols, acronyms like "FGC", "CVM", "IR") that embeddings tend to fuzz.
- **Dense embeddings** with a multilingual model, stored in **`pgvector`** in the same Postgres — handles cross-language retrieval and paraphrase.
- **RRF fusion** of the two ranked lists into one top-K. Both queries hit the same `passages` table; one Postgres round-trip each.

### Embedding-model alternatives (pick one for v1)

| Model | Provider | Multilingual quality | Cost / runtime | Verdict for v1 |
|---|---|---|---|---|
| **`text-embedding-3-large`** | OpenAI | Strong | ~$0.13 / 1M tokens. ~$0.02 to embed the whole corpus once. | **Recommended for v1.** Same provider as the LLM = one credential, one billing line, zero deploy footprint. |
| `text-embedding-3-small` | OpenAI | Decent | ~$0.02 / 1M tokens | Cheaper, weaker on cross-language. Acceptable fallback. |
| `embed-multilingual-v3` | Cohere | Best-in-class for multilingual retrieval | ~$0.10 / 1M tokens | Better quality than OpenAI on cross-language; second provider relationship to manage. |
| `voyage-multilingual-2` | Voyage AI | Strong multilingual | Comparable | Strong but small ecosystem. |
| **`bge-m3`** | Local (HuggingFace) | Strong, open-source benchmark leader | Free runtime cost; ~500 MB model download; ~50 ms per query on CPU | Use when latency matters, when you want zero provider dependency, or when costs grow. Adds deploy footprint. |

**Default for v1:** OpenAI `text-embedding-3-large`. It's the simplest to deploy, costs ~2 cents to bootstrap the corpus, and aligns with using OpenAI as the primary LLM provider.

**Why nothing more is needed at this size:** rerankers add latency and one more model to deploy. The agent loop already compensates for retrieval misses by re-querying. RRF over hybrid is the right default.

**Cost:** one-time embedding pass over the corpus (~$0.02 with `text-embedding-3-large`); per-query cost is one embedding call (~$0.0001 per question).

### Other retrieval strategies considered (and rejected) at this tier

- **BM25 only** — fails cross-language. The corpus is PT/EN; queries are PT/EN/ES. BM25 alone gives bad answers on EN→PT or ES→PT queries.
- **Dense embeddings only** — loses precision on exact-term matches. "CRA-O" or "FGC" need keyword search; embeddings fuzz these.
- **LLM-as-retriever** (ask the model to read the ToC and pick relevant sections) — works at this scale but burns ~5–20× more tokens per query than embedding-based retrieval. Worth re-evaluating *only* if eval shows hybrid retrieval struggles on truly thematic questions. Anthropic's Claude Code uses this pattern at file-system scale, but file systems have natural names and structure that the conviction corpus has too — keep this as a backup option.
- **Provider-hosted retrieval** (OpenAI File Search, Anthropic Citations + custom retriever) — breaks portability; rejected as architecture; lives only inside provider adapters per `ARCHITECTURES.md`.

---

## Why hybrid (BM25 + embeddings) — concrete examples

A reader (or interviewer) asking "why both?" is asking the right question. Here are three real failure modes against this corpus, why each technique handles or misses them, and how RRF fusion combines their strengths.

### Example 1 — Spanish query, Portuguese document

- **Query:** `"tributación de CDB"` (Spanish)
- **Target passage** in `cdbs_quick_guide.md` (Portuguese): `"Tributação de CDB: Imposto de Renda na fonte..."`
- **BM25:** `"tributación"` (ES) does not match `"tributação"` (PT) — different characters (`ó` vs. `ã`, `ón` vs. `ão`). Only `"CDB"` overlaps. **Misses.**
- **Embeddings:** vectors for Spanish `"tributación de CDB"` and Portuguese `"Tributação de CDB"` land in the same neighborhood — same meaning, different surface. **Hits.**

### Example 2 — English query, Portuguese document

- **Query:** `"how is CDB taxed?"` (English)
- **Target passage:** `"Tributação de CDB: Imposto de Renda na fonte..."` (Portuguese)
- **BM25:** zero word overlap except `"CDB"`. **Misses.**
- **Embeddings:** "CDB taxation" and "tributação de CDB" map to the same conceptual region. **Hits.**

### Example 3 — Portuguese paraphrase

- **Query:** `"qual o imposto sobre CDB?"` (PT)
- **Target passage:** `"A tributação dos CDBs segue a tabela regressiva..."` (PT)
- **BM25:** matches `"imposto"` (the passage says "Imposto de Renda" elsewhere) and `"CDB"`. Decent score. **Hits, but middling rank.**
- **Embeddings:** very high similarity — paraphrases of the same question. **Hits, top of the list.**

### Where each technique fails

- **BM25** fails on cross-language and synonym queries. It excels at exact-term matches (acronyms like `FGC`, `CVM`, `IR`; ticker symbols; regulation numbers).
- **Embeddings** fuzz exact terms — `"CRA-O"` (a specific subtype) might pull in `"CRA"` passages about a different subtype because their vectors are close. Embeddings excel at meaning, paraphrase, and cross-language.

### How RRF fuses them

Reciprocal Rank Fusion takes each method's top-K and combines:

```
score(passage) = Σ over each ranking list of 1 / (k + rank_in_list)
                  with k = 60 by convention
```

A passage ranked high in *either* list scores well; a passage ranked high in *both* scores best. Items absent or low in both fall out. The result: BM25's exact-term wins are preserved; embeddings' cross-language and paraphrase wins are preserved; the worst-of-each-method failure modes get filtered out by the other method.

| Failure mode | BM25 alone | Embeddings alone | Hybrid (RRF) |
|---|---|---|---|
| ES query → PT doc (Example 1) | misses | hits | hits |
| EN query → PT doc (Example 2) | misses | hits | hits |
| PT paraphrase (Example 3) | partial | hits | hits, top rank |
| Acronym disambiguation (`CRA-O` vs `CRA`) | hits | fuzzes | hits |

### What this looks like in the implementation

Both retrieval modes are SQL queries against the same `passages` table — that is the payoff of running everything in one Postgres:

```sql
-- Lexical (BM25-style) retrieval
SELECT id, doc_id, heading_path, text,
       ts_rank_cd(tsv, websearch_to_tsquery('simple', :query)) AS lex_score
FROM passages
WHERE tsv @@ websearch_to_tsquery('simple', :query)
ORDER BY lex_score DESC
LIMIT 30;

-- Dense (embedding) retrieval
SELECT id, doc_id, heading_path, text,
       1 - (embedding <=> :query_vector) AS dense_score
FROM passages
ORDER BY embedding <=> :query_vector
LIMIT 30;
```

The application then RRF-fuses the two top-30 lists into a top-K (typically 8) and that's what the agent receives from `search_convictions`. Two SQL statements + a few lines of Python — no vector DB, no search service, nothing extra to operate.

---

## Hundreds (~100–500 docs)

**Stack: hybrid BM25 + dense + cross-encoder reranker.**

- Same retrieval as v1, plus a reranker (`bge-reranker-v2-m3` or Cohere `rerank-multilingual-v3`) that re-scores the top-30 down to the top-8 before sending to the LLM.

- **Why a reranker becomes necessary:** more docs → more near-duplicates and topical neighbors. The fused top-K starts to include passages that *look* relevant but aren't quite. A reranker is a small cross-encoder model that scores `(query, passage)` pairs jointly and is much more precise than independent embedding scores.

- **Cost:** reranker adds ~50–150 ms per query; one extra dependency or provider call.

## Thousands (~1k–10k docs)

**Stack: hybrid + reranker + Anthropic-style Contextual Retrieval.**

- **Contextual Retrieval** — before embedding/indexing each chunk, prepend a generated 50–100 token context summary describing what the chunk is about within its document. Reduces failed retrievals 49% alone, 67% with reranking, per Anthropic's benchmark.

- **Why now:** at this scale, chunks pulled out of context lose meaning ("revenue grew 3%" — for which company, which quarter?). The context summary fixes this.

- **Cost:** one-time per-chunk context generation (~$1 per million doc tokens with prompt caching). One-time only; rebuild on doc changes.

## Tens of thousands and beyond

**Stack: dedicated vector store + dedicated search engine.**

- Promote dense from **`pgvector`** in shared Postgres to a dedicated store like **Qdrant / Weaviate** (or scale Postgres up with HNSW indexes if growth is moderate).
- Promote lexical from Postgres FTS to **OpenSearch / Elasticsearch** or **ParadeDB `pg_search`** (true BM25 inside Postgres) for stronger ranking quality.
- Add **metadata filtering** at both layers (asset class, document language, date range).
- Consider **sharding** by tenant or asset class.

- **Why now:** at this scale, single-Postgres pgvector + FTS becomes a bottleneck on both query latency and indexing throughput. Dedicated stores give HNSW vector indexes, distributed search, replication, and proper operational tooling.

## Quick reference

| Corpus size | Stack | Cost |
|---|---|---|
| ~30–50 (v1) | **Hybrid BM25 + multilingual embeddings + RRF** | ~$0.02 one-time + ~$0.0001 per query |
| Hundreds | + cross-encoder reranker | + ~100 ms / query |
| Thousands | + Contextual Retrieval | + one-time context-generation cost |
| Tens of thousands+ | Real vector store + metadata filtering + sharding | Real infra |

The agent loop, citation contract, and verifier in `ARCHITECTURES.md` stay identical at every scale. Only the *implementation of `search_convictions`* changes. That's the whole point of having retrieval behind a tool boundary.
