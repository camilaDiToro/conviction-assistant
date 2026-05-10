# B6 — decisions log

Per-step decisions for ROADMAP B6 (`search_convictions` — BM25-only retrieval). Companion to:

- `docs/ARCHITECTURES.md` § "Tools layer" for the architectural rules.
- `docs/b5-decisions.md` for the simple-tool conventions B6 inherits.
- `docs/reports/b6-eval-results.md` — the empirical eval outcome (overall 69%; per-bucket breakdown).
- `docs/reports/b6-eval-methodology.md` — how the fixture was authored, what scoring rule the test gates on, and the open scoring options for the user.
- `docs/reports/b6-improvement-proposals.md` — alternative retrieval approaches (hybrid, BM25 tuning, query expansion); designed but not built.

This file captures the *step-local* B6 decisions — return shape, tokenization policy, lifecycle, fixture interpretation — that don't rise to architecture but should be visible to a reviewer.

---

## Why BM25 (and not embeddings) for v1

BM25 is the **lexical baseline that most production retrieval systems still anchor on, even after they add embeddings**. It scores each passage by how many query terms it contains, weighted by:
- **Term rarity** (rare words count more — `come-cotas` outweighs `o`),
- **Term frequency** in the passage (more mentions = more relevant, with diminishing returns),
- **Passage length** (longer passages get a small penalty so a single mention in a giant doc doesn't dominate).

Why we picked BM25 first instead of jumping to embeddings:

1. **The corpus is 30 docs / 423 passages.** At this scale, hand-eval shows that ~70% of realistic queries use the actual terms from the document (literal: 16/29 cases). BM25 hits 93.8% on the literal bucket essentially for free. There's no reason to spend tokens embedding 423 passages to solve a problem BM25 already solves.
2. **It's deterministic and debuggable.** Given a passage and a query, we can compute the score by hand. When something fails (`pgbl-vgbl-diferenca-pt-literal`) we can read the algorithm and explain *why*. Embeddings give a number we mostly can't explain.
3. **It costs zero per query and zero per ingest.** No API calls, no embedding model, no cache to invalidate. The whole index is a numpy matrix in RAM.
4. **It's the right v1 in the "ship the simplest thing that could work, measure, then upgrade" sense.** The eval (`b6-eval-results.md`) tells us where BM25 falls short — paraphrase (5/8) and cross-language (0/5) — and that's exactly where embeddings shine. We get to make the upgrade case from data, not from a vibe.
5. **It's the correct *first* layer of a hybrid system anyway.** When B6.5 lands, it'll be BM25 + dense + RRF, not dense-only. The BM25 work isn't thrown away; it gets fused.

The level-up to hybrid retrieval is documented in `docs/reports/b6-improvement-proposals.md`. Promotion is gated on a conversation with the project owner, not auto-triggered.

## Why NFKD (accent-stripping) in the tokenizer

BM25 sees tokens as opaque byte strings. `tributação` and `tributacao` are different tokens unless we normalize them.

`NFKD` is one of four standard Unicode normalization forms. It decomposes composed characters into their base + combining-mark form, so `ã` (one codepoint) becomes `a` + combining-tilde (two codepoints). Once we drop combining marks, we're left with `a`. Run that on every token and `tributação` collapses to `tributacao`.

Why NFKD specifically (vs the other three forms):
- **NFC** = canonical composed (the *opposite* of what we want).
- **NFD** = canonical decomposed. Would also work for accent-stripping, but doesn't decompose compatibility characters like ﬁ → fi or full-width ‘Ｃ’ → ‘C’. NFKD does.
- **NFKC** = compatibility composed. Recomposes after the compatibility decomposition. We don't want recomposition because we're about to strip combining marks.
- **NFKD** = compatibility decomposed. Maximum decomposition, gives us the most aggressive accent + compatibility stripping. Right tool for a recall-focused tokenizer.

What this buys us in practice:
- A user typing `tributacao` (no accents — common on phones) matches passages saying `tributação`.
- `Cómo` (ES query) matches `como`. `pequeña` matches `pequena`. `mecânica` matches `mecanica`.
- Compatibility forms like `ﬁnance` (the U+FB01 ligature) collapse to `finance`. Rare in our corpus but cheap to handle.

The pipeline must be **symmetric** — same `_normalize()` runs on both indexed passages and incoming queries. If only one side is normalized, the tokens never align and BM25 returns nothing. The unit tests in `tests/services/test_search.py` cover this.

NFKD-normalize-and-strip is **independent of the verifier's normalization** (B7), which preserves diacritics so cited quotes round-trip to the source unchanged. The two layers serve different purposes: search-tokenizer normalization is a *recall* concern (we want `tributacao` to find `tributação`); verifier normalization is a *fidelity* concern (the user must see the quote exactly as it appears in the source).

---

## Return shape — `PassageHit`

`search_convictions(query, k=5) -> list[PassageHit]`. Fields (`app/schemas/passage.py`):

| Field             | Type            | Why                                                                     |
|-------------------|-----------------|-------------------------------------------------------------------------|
| `passage_id`      | `str`           | Stable slug-based identifier; the agent passes this to `read_passage`.  |
| `score`           | `float`         | Raw BM25 score. Not normalized to `[0,1]` — it's only useful as a relative rank within one query. |
| `document_id`     | `str`           | Lets the agent inspect the document's other passages without re-grouping. |
| `document_title`  | `str`           | For citation rendering (the user-facing footer).                        |
| `heading_path`    | `list[str]`     | Citation enrichment without an extra round-trip.                        |
| `snippet`         | `str` (≤ ~200c) | First word-boundary-cut excerpt of `passage.text`. Lets the agent skim before deciding to `read_passage`. |
| `document_updated`| `date \| None`  | **Required for Rule B** — agent compares dates to surface conflicting convictions. Missing for 16 of 30 docs (verified 2026-05-09); never inferred. |

`PassageHit` is intentionally **richer than `Passage`** (which `read_passage` returns). The two shapes serve different purposes: `read_passage` is the source-of-truth full body; `PassageHit` carries search-only metadata (score, snippet) for the agent's evidence-gathering loop. This was a deliberate departure from b5-decisions.md's expectation that `search_convictions` would return `Passage`.

## Tokenization policy (pinned)

The same pipeline runs against both indexed passages and incoming queries:

1. **NFKD unicode normalization** + drop combining marks → accent-strip.
2. **Lowercase**.
3. **Collapse runs of whitespace** to a single space.
4. **`bm25s.tokenize(..., stopwords=None, stemmer=None)`** — default `\W+` split.

Rationale:
- One pipeline for PT/EN/ES instead of per-language stemmer routing. Predictable, easy to test, no Snowball-stemmer drift.
- Accent-strip handles `tributação` ↔ `tributacao` for users who type without diacritics.
- **No stopwords** because at this corpus size, dropping common words can hurt unique-phrase queries (e.g. "a tabela regressiva"). Tested in `tests/services/test_search.py`.
- **No stemmer** because Brazilian Portuguese stemming is approximate and would couple the index to a language-detection step. The recall ceiling we lose is not the gap we need to close — see improvement-proposals doc.

This normalization is **independent of the verifier's normalization** (B7), which preserves diacritics so cited quotes round-trip to the source. Search normalization is a recall concern; verifier normalization is a fidelity concern.

## Empty-query semantics

| Input            | Behavior                                |
|------------------|-----------------------------------------|
| `""`             | raise `EmptyQueryError`                 |
| `"   \t\n"`      | raise `EmptyQueryError` (post-strip)    |
| Non-empty corpus | top-k by BM25                           |
| Empty corpus     | return `[]` (pre-ingest is normal)      |

`EmptyQueryError` is a `DomainError` subclass mapped to HTTP 400 in `app/main.py` so the future agent loop (B8) can feed it back as a tool-error message and the future `/chat` endpoint (B9) doesn't 500 on a malformed query.

## How the flow works

The BM25 index is **in-memory only** and lives on `app.state.search_index` for the life of the process. There are exactly three flows that touch it: startup, re-ingest, and per-query.

### Flow 1 — startup (cold boot)

Runs once when `uvicorn` starts the FastAPI app. Defined in `app/main.py` `lifespan()`:

```
1. db.migrate(sqlite_path)                         # alembic → schema is current
2. engine = db.make_engine(async_database_url)     # SQLAlchemy async engine
3. factory = db.make_session_factory(engine)
4. db.set_session_factory(factory)                 # global, used by /admin and /chat handlers
5. index = BM25Index()                             # empty: 0 passages, no retriever
6. async with factory() as session:
       await index.build(session)                  # ── reads passages, tokenizes, indexes
7. app.state.search_index = index                  # attach to app for handlers to reach
8. yield                                           # FastAPI starts serving requests
```

What `index.build(session)` does inside step 6:
- Calls `passages_repo.iter_all(session)` → one bulk SELECT returning every passage as a `Passage` object.
- For each passage, runs `_normalize(p.text)` (NFKD strip-accents → lowercase → collapse whitespace).
- Hands the normalized strings to `bm25s.tokenize(stopwords=None, stemmer=None)` to get integer token streams.
- Hands the tokens to `bm25s.BM25().index()` which builds the inverted index in RAM.

**Empty-DB cold start is supported:** if the `passages` table is empty (e.g. very first boot before any ingest has run), `iter_all` returns `[]`, the index has zero passages, and any call to `search()` returns `[]` until a `POST /admin/ingest` runs. No errors, no warnings — pre-ingest is a normal state.

**Why startup is the right place:** building the index is ~30–100 ms for 30 docs. Doing it lazily on the first query would burn that latency on a real user. Doing it per-query would burn it on every request. Building once at boot and sharing across requests is the obvious right answer at this scale.

### Flow 2 — re-ingest (`POST /admin/ingest`)

The corpus changes (a conviction was edited, a new doc was added) by re-running ingest. Defined in `app/api/admin.py`:

```
1. report = await ingest_service.ingest_corpus(session, settings.convictions_dir)
       # parser walks convictions/*.md
       # async with session.begin():
       #   upsert all passages
       #   delete orphans (renamed-heading slugs)
       # commit
2. await request.app.state.search_index.rebuild(session)
       # same code path as build(): iter_all + tokenize + reindex
3. return IngestResponse(...)
```

**Why rebuild synchronously inside the request:** the response returns only after the index has been rebuilt, so the very next `/chat` call sees the freshly-ingested passages. If we rebuilt in a background task, there'd be a window where the DB has new passages but the index doesn't — searches would silently miss new content.

**Why a full rebuild instead of an incremental update:** at 30 docs, full rebuild is faster than the bookkeeping required to track which passages changed and patch the inverted index in place. The level-up path (incremental updates, on-disk persistence via `bm25s.BM25.save()`) is documented but not built — it becomes worth it past ~thousands of docs.

### Flow 3 — per query (`search_convictions`)

The agent (or any direct caller) calls the tool. Defined in `app/tools/search_convictions.py`:

```
1. tool wrapper validates query is non-empty       → EmptyQueryError on empty/whitespace
2. ctx.search_index.search(query, k)
       # _normalize(query)                         ← SAME pipeline as build time
       # bm25s.tokenize([normalized_query])
       # retriever.retrieve(query_tokens, k=k)     ← scores all 423 passages, returns top-k indices
       # map each (idx, score) → (Passage, score)
3. for each (passage, score):
       PassageHit(
           passage_id, score,
           document_id, document_title, heading_path,
           snippet=_make_snippet(passage.text),
           document_updated,                       ← required for Rule B
       )
4. return list[PassageHit]
```

**No DB access during this flow.** The repository is touched only at build time (flow 1) and rebuild time (flow 2). Per-query work is pure in-RAM lookup, which is why p95 latency is ~2 ms even on the slowest fixture cases.

### Properties this design buys

- **Build is idempotent.** `BM25Index.build()` may be called any number of times; each call replaces prior state. Tests rely on this.
- **Symmetric normalization.** Build and query both call `_normalize()`. If anyone changes one without the other, every query silently loses recall — covered by the unit tests in `tests/services/test_search.py`.
- **Tool surface is stable across upgrades.** The agent calls `search_convictions` and gets `list[PassageHit]`. When B6.5 adds dense embeddings + RRF, only the `BM25Index` instance gets wrapped in a `HybridIndex`; the tool wrapper, `ToolContext`, and the agent loop don't change.
- **No on-disk index file.** `bm25s.BM25.save()` exists but isn't used. At 30 docs the rebuild is fast enough that persistence buys nothing and the failure mode (stale index file vs current DB) isn't worth defending against.

## Tool function signature

```python
async def search_convictions(
    ctx: ToolContext,
    *,
    query: str,
    k: int = 5,
) -> list[PassageHit]
```

- `ctx` positional; everything else keyword-only.
- `k` is required in the JSON schema (OpenAI strict mode forbids parameter defaults inside the schema), but defaults in the Python signature so direct Python callers and unit tests don't have to thread it through.
- The schema description tells the model "Pass 5 unless you have a reason to change it; larger k dilutes precision."

## Fixture interpretation and test gate

The acceptance test reads `tests/fixtures/retrieval_golden.yaml` (29 hand-authored cases). The test computes **two scores per case** and prints both per-bucket; only the primary score gates:

- **Primary score** (the gate): 1 if `expected_passage_ids[0]` in top-5, else 0.
- **Weighted score** (printed alongside): 1.0 if primary in top-5; 0.5 if any secondary in top-5; else 0.0. Encodes "you found a legitimate but secondary passage".

Per-bucket floors on the primary score:

- `literal` ≥ 90% (currently 93.8%).
- `topic` ≥ 50% (currently 62.5%).
- `cross_lang` reported only, not asserted (currently 0/5; canary for the hybrid level-up).
- `p95 latency < 50 ms` (currently ~2 ms).

At today's BM25 baseline the weighted score equals the primary score (no failing case has its secondary in top-5). The divergence will become meaningful once hybrid retrieval lands. Full methodology — including how cases were built, how they're tested, and how scores are calculated — lives in `docs/reports/b6-eval-methodology.md`.

The breakdown is **printed every test run** so the per-bucket numbers are visible without re-running with `-s`. Pytest also dumps stdout on failure, so a regression surfaces with the full diagnostic in the failure output.

## What B6 deliberately did NOT do

Each item below has a documented level-up path in `docs/reports/b6-improvement-proposals.md`:

- **No embeddings** — `EmbeddingProvider` ships in B4 but B6 does not import it. Hybrid retrieval is the documented next step (B6.5) if the user agrees.
- **No fusion** (RRF, weighted combine).
- **No cross-encoder reranker.**
- **No query expansion** (cognate dictionary, character-n-gram index).
- **No on-disk persistence** of the BM25 index — rebuilt from passages each startup.
- **No stopword lists, no stemmer.**
- **No per-language indexes** — one shared index, accent-stripped tokenization handles PT/ES surface variants.
- **No tuning of `k1`/`b`/method.** bm25s defaults (`method="lucene", k1=1.5, b=0.75`); the case for tuning is in proposals.

## Files touched in B6

**Created:**
- `app/services/search.py` — `BM25Index`, `_normalize`, `_make_snippet`.
- `app/tools/search_convictions.py` — tool wrapper.
- `tests/services/test_search.py` — unit tests for normalize / snippet / index lifecycle.
- `tests/tools/test_search_convictions.py` — acceptance test (golden fixture + empty-query + metadata shape).
- `docs/b6-decisions.md` — this file.
- `docs/reports/b6-eval-results.md`, `docs/reports/b6-eval-methodology.md`, `docs/reports/b6-improvement-proposals.md`.

**Edited:**
- `app/schemas/passage.py` — added `PassageHit`.
- `app/schemas/__init__.py` — re-export `PassageHit`.
- `app/errors.py` — added `EmptyQueryError`.
- `app/repositories/passages.py` — added `iter_all` (bulk load passages with full text).
- `app/tools/context.py` — `ToolContext` now carries `search_index: BM25Index`.
- `app/tools/registry.py` — registered `search_convictions` (definition + JSON schema).
- `app/tools/__init__.py` — re-export `search_convictions` and `SEARCH_CONVICTIONS_DEF`.
- `app/main.py` — lifespan builds the index; `EmptyQueryError` mapped to HTTP 400.
- `app/api/admin.py` — admin ingest calls `request.app.state.search_index.rebuild()`.
- `tests/tools/test_simple_tools.py` — `ToolContext` construction updated; registry test now expects 4 tools.
- `pyproject.toml` — added `bm25s` (and its numpy/scipy footprint).
