# Deployment — Decade AI Challenge

The concrete deploy plan: technologies, where things run, the architecture diagram, and the key decisions with their rationale. Companion to `ARCHITECTURES.md` (which describes the *system*) and `SCALING.md` (which describes how things change at higher tiers).

---

## Architecture diagram

```
                              ┌─────────────────────────────────────┐
                              │           Browser (analyst)         │
                              │   Vite-built static React bundle    │
                              │       (TypeScript + Tailwind)       │
                              └─────────────────┬───────────────────┘
                                                │  HTTPS
                                                ▼
┌──────────────────────────────────────────────────────────────────────┐
│                      Single deployed service                         │
│                  Python 3.12 · FastAPI · uvicorn                     │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                    GET /            (Vite-built React app)   │   │
│  │                    POST /chat       (the conversation API)   │   │
│  │                    GET  /health     (platform health probe)  │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  Conversation orchestrator                                    │   │
│  │    ↓                                                          │   │
│  │  Agent loop (gather → act → verify), bounded                  │   │
│  │    ↓                                                          │   │
│  │  Tools: list_documents · read_document_outline ·              │   │
│  │         search_convictions · read_passage                     │   │
│  │    ↓                                                          │   │
│  │  Citation verifier (deterministic) → retry once → response    │   │
│  └──────────────────────────────────────────────────────────────┘   │
└──────┬───────────────────────────────────────┬───────────────────────┘
       │                                       │
       ▼                                       ▼
┌────────────────────────────────────┐  ┌────────────────────────────────────┐
│  Postgres + pgvector + unaccent    │  │  External providers (over HTTPS)    │
│  (Neon / Supabase / RDS / docker)  │  │                                     │
│                                    │  │  ┌──────────────────────────────┐  │
│  Knowledge base (synced from       │  │  │ OpenAI (primary, v1)         │  │
│  convictions/ at startup):         │  │  │  • gpt-5                     │  │
│   • passages                       │  │  │  • text-embedding-3-large    │  │
│       - text, heading_path,        │  │  └──────────────────────────────┘  │
│         language                   │  │  ┌──────────────────────────────┐  │
│       - tsv  (Postgres FTS)        │  │  │ Anthropic (second adapter)   │  │
│       - embedding (pgvector)       │  │  │  • claude-opus-4-7           │  │
│                                    │  │  │    (portability proof)       │  │
│  Operational state:                │  │  └──────────────────────────────┘  │
│   • conversations                  │  └────────────────────────────────────┘
│   • audit_log                      │
│   • cost_log                       │
│                                    │
│  ONE DATABASE_URL — local docker   │
│  for dev, Neon when hosted.        │
└────────────────────────────────────┘
```

### What lives where — one Postgres for everything

A single **Postgres database (with `pgvector` and `unaccent` extensions)** holds every persistent piece of state. No SQLite, no in-memory index, no second store to coordinate.

```
postgres ←── all schema below ──→
  passages (
    id, document_id, heading_path[], language, text,
    tsv          tsvector  GENERATED ALWAYS AS (...),  -- BM25-style FTS
    embedding    vector(3072)                          -- pgvector
  )
  conversations ( id, created_at, ... )
  conversation_messages ( id, conversation_id, role, content, created_at )
  audit_log ( step_id, question_id, conversation_id, kind, payload, usage, ts )
  cost_log  ( ... mirror of audit_log restricted to llm_call rows ... )
```

#### How the conviction knowledge base lives in this DB

At startup, the service reads `convictions/*.md`, parses each file into passages, computes embeddings via OpenAI, and **upserts** into the `passages` table. To avoid pointless re-embedding on every restart we hash each `.md` file and skip rows whose source hash matches what's already in the DB. So:

- **Cold start (first deploy or after a corpus edit):** ~2 seconds parsing + ~$0.02 OpenAI embedding cost. Persisted once.
- **Warm restart (no corpus change):** instantaneous; the DB already has the passages and vectors.

Both BM25 and dense retrieval run as **SQL queries** against this same table:

- BM25: `WHERE tsv @@ websearch_to_tsquery(...) ORDER BY ts_rank_cd(...)`.
- Dense: `ORDER BY embedding <=> $query_vector` (cosine distance via pgvector).
- The two ranked lists fuse with RRF in application code → top-K passages.

#### Why a single Postgres beats the previous "two-store" plan

| Concern | Two stores (in-memory + Postgres) | Single Postgres |
|---|---|---|
| Mental model | Two stores, sync rules, hash-check at boot | One store, one ORM, one URL |
| Restart cost | Re-embed every cold start (~$0.02) | Pay once; warm restarts are free |
| Multi-instance scaling | Each worker re-builds in-memory indexes | Workers share one DB; trivial |
| Hosting | Local SQLite vs. cloud Postgres branching | Same Postgres everywhere |
| Vector store | numpy in-memory | `pgvector` (idiomatic, indexable with HNSW) |
| BM25 | SQLite FTS5 in-memory | Postgres FTS (`tsvector` + `ts_rank_cd`) |

The single-store version is simpler to reason about and removes the "what happens on a restart" question entirely.

#### Where Postgres runs

- **Local dev:** `docker compose up` brings up a Postgres + pgvector container (`pgvector/pgvector:pg16`).
- **Hosted demo:** **Neon free tier** (managed Postgres with pgvector built-in; ~5 s to create a project). Or Supabase free tier; both work.

Same `DATABASE_URL`, same SQLAlchemy code, same schema in both places.

---

## Technology stack

### Backend

| Layer | Choice | Why |
|---|---|---|
| Language | **Python 3.12** | Best ecosystem for LLM work; matches what Decade likely uses. |
| Web framework | **FastAPI** | Async, Pydantic-native, OpenAPI for free. |
| ASGI server | **uvicorn** (single worker for v1) | Single instance is the v1 assumption per `ASSUMPTIONS.md`. |
| Schemas | **Pydantic v2** | The citation contract (`docs/ARCHITECTURES.md` § "Response contract") is already shaped like Pydantic. Schema validation is a real safety layer. |
| LLM provider (primary) | **OpenAI `gpt-5`** | Per `ASSUMPTIONS.md`. Same provider for LLM and embeddings = one credential. |
| LLM provider (second) | **Anthropic `claude-opus-4-7`** | Implemented to prove the portability requirement. |
| Embeddings | **OpenAI `text-embedding-3-large`** | Multilingual; ~$0.02 to embed the whole corpus. See `RETRIEVAL_SCALE.md`. |
| BM25 (lexical) | **Postgres FTS** (`tsvector` + `to_tsvector` + `ts_rank_cd` + `unaccent` ext) | Built into Postgres; no extra service. Multilingual handled by `simple` config + `unaccent` for PT/EN/ES coverage. Promote to ParadeDB `pg_search` (true BM25) only if `ts_rank_cd` proves insufficient. |
| Vector index | **`pgvector`** in the same Postgres | Idiomatic; one DB; HNSW index when scale demands; works on Neon out-of-the-box. |
| Provider SDKs | **`openai`, `anthropic`** | Direct SDKs; no LangChain (per `CLAUDE.md` design principles). |
| HTTP client | **httpx** | What both SDKs use; consistent. |
| Database | **Postgres 16+ with `pgvector` and `unaccent` extensions** | One DB for passages, FTS index, embeddings, conversations, audit, cost. Local dev via docker compose; hosted via Neon free tier (pgvector built-in). |
| ORM | **SQLAlchemy 2.0** | Five tables. The pgvector column type has a SQLAlchemy adapter (`pgvector.sqlalchemy.Vector`). |
| Logging | **structlog** | JSON-line output; same payload powers the audit log. |
| Tests | **pytest + pytest-asyncio** | Standard. |
| Eval | **DeepEval** | `pytest`-native, gates cleanly. Per `TESTING.md`. |
| Lint/format | **ruff** | One tool replaces black + isort + flake8. |
| Type-check | **mypy** in CI | Catches schema drift early. |
| Package mgmt | **uv** | Fast, single `pyproject.toml`. |

### Frontend — Vite + React + TypeScript + Tailwind

The lightest *real React* setup. Single-page app, builds to plain static files, no SSR, no node runtime in production.

```
frontend/
  index.html
  vite.config.ts
  tsconfig.json
  package.json
  src/
    main.tsx              # entry
    App.tsx               # the only page (a chat)
    api.ts                # fetch /chat, type-check the response
    types.ts              # mirrors app/api/schemas.py
    components/
      Chat.tsx
      Message.tsx         # citations + general-knowledge banner + conflict callout
      DebugDrawer.tsx     # tool trace, per-step cost, verifier result
      Disclaimer.tsx
```

Build: `npm run build` → `frontend/dist/` of plain HTML/CSS/JS. **FastAPI mounts this `dist/` at `/`**, so it's a single deploy, single URL, no CORS, no FE platform to manage. (Alternative: deploy `dist/` separately to Vercel and point at the API by URL — slightly more configuration, but cleanly splits FE/BE if you prefer.)

Why this shape (still light, but real React):

- **Vite, not Next.js.** No SSR, no node runtime, no `next.config.js`. The build output is plain static files.
- **No state library** — chat is a list of messages and a draft input; `useState` and `useReducer` are enough.
- **No router** — one page, no navigation.
- **TypeScript** — catches drift between BE schemas and FE types early. The response shape is non-trivial (`kind` discriminator, citations, general-knowledge fields, debug payload), and TS makes that drift loud.
- **Tailwind** — utility classes; no design system overhead. Works fine with Vite's PostCSS pipeline.

What the page renders (unchanged from the previous plan):

- Chat thread (user / assistant turns).
- **Citations** as expandable cards: click → expand the full passage with heading path.
- **General-knowledge banner** (Rule A): when `general_knowledge_used: true`, render a visually distinct block above the answer.
- **Conflict callout** (Rule B): when the response cites contradictory convictions, render them side-by-side.
- **Disclaimer footer**, always visible.
- **Debug drawer** (collapsed by default): tool trace + per-step cost + verifier pass/fail. **Single highest-ROI feature — makes the whole architecture visible in 5 seconds during the demo.**
- **Cost meter** badge: "this conversation cost $0.04" from `usage_summary.conversation_total_cost_usd`.

The build step is the only complexity added vs. plain HTML; in return you get TypeScript types, sane component decomposition, and a stack the interviewer recognizes immediately.

---

## Where to deploy

Ranked from simplest to most production-shaped.

| Option | Cost | Persistent state? | Cold-start | Pick for |
|---|---|---|---|---|
| **Local + ngrok** | $0 | Trivially (your laptop) | n/a | **Recommended for the demo.** No surprises, can poke around live. |
| **Render (free tier)** | $0 | Postgres add-on free | Sleeps after 15 min idle | If you want a stable hosted URL. |
| **Fly.io (free credit)** | ~$0 | Volume + Fly Postgres | Cold-start <10s | Pick São Paulo region for low latency. |
| **Railway** | ~$5/mo | Postgres included | None | If you want zero ops time and a paid tier. |

### Recommended for the interview submission: **local + ngrok**

- `docker compose up postgres` (Postgres 16 + pgvector). Or point at Neon's free tier from the start.
- `uvicorn app.main:app` on your laptop.
- `ngrok http 8000` to get a public URL for the screen share.
- No cold-start surprises. No platform-specific weirdness. If the interviewer asks "show me the audit log" you can run `psql` against the same DB live.

### If you want a hosted URL anyway: **Render + Neon**

- Backend: Render free web service (Docker or buildpack), serving FastAPI + the built React FE under `/`.
- Postgres: Neon free tier (pgvector enabled by default).
- Connect via the `DATABASE_URL` env var.
- One domain, no CORS, single-region.
- Acceptable cold-start for an interview link.

---

## Configuration

Environment variables (twelve-factor):

```
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...        # only if Anthropic adapter is exercised
PROVIDER=openai                     # or "anthropic"
LLM_MODEL=gpt-5                     # default per provider
EMBEDDING_MODEL=text-embedding-3-large
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/decade   # local docker
                                                                   # same shape on Neon
LOG_LEVEL=INFO
API_KEY=...                         # optional shared secret for /chat
```

`.env.example` committed; `.env` gitignored.

---

## Project layout

```
decade-ai-challenge/
├── AI_CHALLENGE.md
├── CLAUDE.md
├── README.md                          # the deliverable Decade reads
├── pyproject.toml
├── .env.example
├── convictions/                       # the corpus (committed)
├── docs/                              # design docs (this folder)
├── app/
│   ├── __init__.py
│   ├── main.py                        # FastAPI app + static mount + /chat /health
│   ├── config.py                      # env vars, model picks, prices
│   ├── parser/
│   │   ├── markdown.py                # markdown → passages
│   │   └── interface.py               # DocumentParser protocol
│   ├── store/
│   │   ├── passages.py                # SQLAlchemy model + ingestion (sync from convictions/)
│   │   ├── search.py                  # hybrid Postgres FTS + pgvector + RRF
│   │   ├── embeddings.py              # OpenAI embedding calls + upsert
│   │   ├── conversations.py           # Postgres conversation state
│   │   └── audit.py                   # Postgres per-step audit log (token counts only)
│   ├── services/
│   │   └── cost.py                    # USD via vendored model prices (read-time)
│   ├── tools/
│   │   ├── definitions.py             # JSON schemas for the four tools
│   │   └── runtime.py                 # dispatch tool calls to store
│   ├── providers/
│   │   ├── llm_base.py                # LLMProvider Protocol
│   │   ├── llm_openai.py              # ← primary
│   │   ├── llm_anthropic.py           # ← second adapter, portability proof
│   │   ├── embed_base.py              # EmbeddingProvider Protocol
│   │   └── embed_openai.py            # ← primary
│   ├── orchestrator/
│   │   ├── loop.py                    # gather → act → verify
│   │   ├── verifier.py                # substring verifier + retry
│   │   └── disclaimer.py              # deterministic append
│   ├── api/
│   │   ├── schemas.py                 # Pydantic request/response models
│   │   └── routes.py                  # FastAPI routers
│   └── static/                        # FastAPI mounts frontend/dist/ here at /
├── frontend/                          # Vite + React + TS + Tailwind
│   ├── index.html
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── api.ts
│       ├── types.ts
│       └── components/
│           ├── Chat.tsx
│           ├── Message.tsx
│           ├── DebugDrawer.tsx
│           └── Disclaimer.tsx
├── tests/                             # pytest, no LLM
└── eval/                              # pytest -m eval; uses real provider
    ├── golden.json
    └── test_buckets.py
```

This shape maps 1:1 to `ARCHITECTURES.md` and `TESTING.md` so the interviewer can find any component in the directory it ought to be in.

---

## Key technical decisions (and why)

### 1. Hybrid BM25 + multilingual embeddings, not BM25-only

**Why:** the corpus is PT/EN; queries are PT/EN/ES. BM25 alone has a cross-language failure mode ("CDB taxation" doesn't match "tributação de CDB"). Multilingual embeddings bridge the languages; BM25 still wins on exact-term matches (acronyms, ticker symbols). RRF fusion is the simplest combiner. See `RETRIEVAL_SCALE.md`.

### 2. OpenAI as primary, Anthropic as second adapter

**Why:** Per `ASSUMPTIONS.md`, no provider is restricted. Picking OpenAI as primary gives one provider for both LLM (`gpt-5`) and embeddings (`text-embedding-3-large`) — single credential, single billing line. The Anthropic adapter is implemented second specifically to prove the portability requirement isn't theoretical.

### 3. One Postgres for everything, no SQLite, no in-memory store

**Why:** A single Postgres database (with `pgvector` and `unaccent`) holds the passage table, the FTS index, the embeddings, conversations, the audit log, and the cost log. One mental model, one connection string, one ORM, one schema migration story. Local dev runs Postgres via docker compose; hosted runs Neon (free tier with pgvector built-in). This removes the awkward "in-memory store + persistent store" split, removes the "what happens on cold start" question (warm restarts are instant; embeddings persist), and matches what scaling looks like — at every tier we still have one Postgres, just bigger.

### 4. pgvector + Postgres FTS, not a separate vector DB or search engine

**Why:** At v1 scale (~30 docs → a few hundred passages), running a separate vector DB or search engine is pure overhead. `pgvector` does cosine similarity inside Postgres; `tsvector` + `ts_rank_cd` does BM25-style lexical scoring; both are SQL queries against the same `passages` table. The retrieval code is two SQL statements + RRF in Python. Promotion to a dedicated vector store (Qdrant / Weaviate) or search engine (OpenSearch / ParadeDB `pg_search`) happens only when the corpus reaches thousands of docs (see `RETRIEVAL_SCALE.md`).

### 5. Vite + React + TypeScript + Tailwind, not Next.js (and not vanilla)

**Why:** The lightest *real React* setup. Vite produces plain static files with no SSR or node runtime, so the build output mounts cleanly under FastAPI as `/`. TypeScript catches BE/FE schema drift cheaply (the response shape has a discriminated union and several optional fields). Next.js would add an SSR runtime that buys nothing here. Vanilla JS would work too but loses type-safety on a non-trivial schema. This sits at the right point on the simplicity/correctness curve for a real React app.

### 6. Local + ngrok for the actual demo

**Why:** Cold starts on free tiers introduce flakiness exactly when you don't want it. Running locally with ngrok eliminates platform variance, lets you inspect logs / Postgres / audit log live during the discussion, and is closer to what most interviewees actually do.

### 7. Postgres FTS for BM25, not Elasticsearch / OpenSearch

**Why:** Postgres has built-in full-text search (`tsvector`, `to_tsvector`, `ts_rank_cd`). With `unaccent` it handles PT/EN/ES decently. Zero extra infra. Elasticsearch / OpenSearch / ParadeDB `pg_search` are correct at thousands+ docs and are documented in `RETRIEVAL_SCALE.md` for that tier; for v1, Postgres FTS is plenty.

### 8. No LangChain / LlamaIndex

**Why:** Direct provider SDKs (OpenAI, Anthropic) plus our own `LLMProvider` protocol. LangChain in 2026 is a red flag in interviews focused on "do you understand the system." The provider abstraction we already designed is the right shape and one we can defend without explaining a third-party framework's quirks.

### 9. uv for package management

**Why:** Faster than pip, no `requirements.txt` ritual, single `pyproject.toml`. Standard in 2026 Python projects.

---

## What changes for scale

Pasted from `SCALING.md` for the deployment context:

### v1 (current, <10 concurrent users)

What's described above. Single uvicorn instance + Neon free Postgres + OpenAI provider.

### 10–100 concurrent users

| Component | v1 | At 10–100 |
|---|---|---|
| Web | 1 uvicorn | gunicorn + N uvicorn workers behind a load balancer |
| Index (BM25 + dense) | In-process per worker | Either: keep per-worker (rebuild on cold start, ~2 s) — fine; or move to a shared cache. |
| Conversation state | Postgres | Add **Redis** in front for hot reads + rate-limit token buckets |
| Provider failures | Fail open | Retry + circuit breaker per provider |
| Auth | API key | OAuth/JWT |
| Observability | JSONL audit log | OpenTelemetry traces + log destination |

The agent loop, citation contract, and verifier are **unchanged**. The provider abstraction means the LLM swap is also unchanged.

### 100+ concurrent users

| Component | At 10–100 | At 100+ |
|---|---|---|
| Search | Postgres FTS | **OpenSearch / Elasticsearch / ParadeDB `pg_search`** (true BM25) |
| Vector store | numpy in-process | **pgvector / Qdrant / Weaviate** |
| Workload | Sync per request | **Queue** (Celery / Arq / Temporal) — API enqueues, worker runs |
| Provider | Single primary | Multi-provider with health checks + failover |
| Costs | Tracked | **Enforced** — per-user budgets gate new requests |

Again, the agent loop and verifier stay identical. The seams are designed for exactly this kind of swap.

See `docs/SCALING.md` for the full breakdown and `docs/RETRIEVAL_SCALE.md` for the corpus-driven side of the story.

---

## Smoke checklist before submitting

- [ ] `uvicorn app.main:app` starts cleanly with no errors in the log.
- [ ] `/health` returns 200.
- [ ] `/` renders the chat UI.
- [ ] A simple in-scope question (PT) returns an answer with a verified citation, the disclaimer, and a non-empty `usage_summary`.
- [ ] An in-scope question in EN over a PT-only document still finds the right passage (cross-language sanity).
- [ ] An out-of-scope question returns a `general_knowledge_section` with the unambiguous marker.
- [ ] A constructed conflict question cites both convictions and states the disagreement.
- [ ] The debug drawer in the FE shows the tool trace and per-step cost.
- [ ] `pytest` (no LLM) is green.
- [ ] `pytest -m eval` (real provider) hits 100% verifier pass rate on the smoke subset.
- [ ] README links to `docs/`, names the chosen architecture in the first paragraph, and has a "production-readiness" section pointing at `SCALING.md`.
