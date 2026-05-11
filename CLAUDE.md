# CLAUDE.md — Decade AI Challenge

Index for future Claude sessions working on this project. Read this first; follow the pointers.

## What this project is

A conversational AI assistant strictly grounded on Decade's investment conviction documents. The challenge brief is in `AI_CHALLENGE.md`. The corpus is in `convictions/` (30 markdown files, mixed Portuguese/English, expected to grow).

**One-line framing for the interview:** *deterministic offset-based provenance as the grounding guarantee — every citation resolves to a `(start, end)` region of the source passage, and the UI shows the user exactly what was cited. Paired with a constrained agentic harness (small read-only tool surface + bounded gather→act loop) whose discipline is inspired by Claude Code. No provider's Citations API matches this guarantee.*

The architecture is a **deterministic offset resolver + constrained tool-using agent**: the model gets read-only tools over a passage store and produces structured answers; every cited quote is resolved to character offsets in the cited passage before the response is built. The literal quote is dropped — only `(passage_id, start, end)` survives into the wire response. Citations whose quotes don't anchor still surface; the popup shows the passage without a highlight.

## Stack

- **Python 3.12**, FastAPI, **SQLAlchemy 2.x async** with **aiosqlite**, **Pydantic v2**
- **Alembic** for migrations, **uv** for package management, **pytest** (+ `pytest-asyncio` in `auto` mode) for testing, **ruff** + **mypy** for lint/type-check

## Common commands

| Action | Command |
|---|---|
| Dev server | `uv run uvicorn app.main:app --reload` |
| Tests | `uv run pytest -xvs` |
| Tests + coverage | `uv run pytest --cov=app --cov-report=term-missing` |
| Lint + format + type-check | `uv run ruff check . && uv run ruff format . && uv run mypy .` |
| New migration | `uv run alembic revision --autogenerate -m "description"` then `uv run alembic upgrade head` |
| Apply pending migrations | `uv run alembic upgrade head` (lifespan applies on app start automatically) |
| Trigger ingest | `curl -X POST http://localhost:8000/api/admin/ingest -H "X-Admin-Token: $ADMIN_TOKEN"` |

## Where to read what

| File | Purpose |
|---|---|
| `AI_CHALLENGE.md` | The challenge brief from Decade. The requirements live here. |
| `docs/ARCHITECTURES.md` | **The chosen architecture.** Tool surface, agent loop, offset resolver, what's *not* implemented in this version, alternatives that were considered and rejected. |
## CRITICAL RULES (these must be obvious in every response)

These are non-negotiable behaviors. They are the "very, very clear" rules — confirmed by the project owner — that must be visible in every answer the assistant produces.

### 🔴 Rule A — General knowledge MUST be marked very, very clearly

The assistant **may** use general knowledge when the convictions don't cover a topic, but it **MUST be made very, very clear** to the user. Specifically:

- **Always prefer a real conviction reference**, even if it mentions the topic only tangentially. The citation must include passage ID + document title + heading path + exact quote, so the analyst can see *where* the convictions mention it.
- **Only fall back to general knowledge when no conviction touches the topic at all.**
- General-knowledge text **must be marked unambiguously** (dedicated section heading like "**Not from Decade convictions — general knowledge:**", or an equivalent visual prefix).
- **Never interleave** general-knowledge claims with conviction-grounded claims in the same paragraph without a clear delimiter.
- The structured response carries `general_knowledge_used: true` and a separate `general_knowledge_section` field — see `docs/ASSUMPTIONS.md` for the schema.

### 🔴 Rule B — Conflicting convictions MUST be surfaced

When two or more convictions contradict each other on a topic:

- **Cite all sides.** Never silently pick one.
- **State explicitly that the convictions disagree.**
- The analyst makes the judgment call; the assistant does not pretend consensus exists.

---

## Other design principles (do not violate)

1. **The agent finds evidence; the resolver pins it to offsets.** These are separate responsibilities. The model is good at copying substrings, bad at counting characters — let it copy, then resolve to `(start, end)` server-side. Don't move grounding logic into the prompt or rely on the model to emit offsets directly.
2. **No provider-native grounding feature is the architecture.** They live behind adapters as optimizations only. The contract above the adapter is identical across Anthropic, OpenAI, Gemini.
3. **BM25-only is the v1 retrieval baseline.** The corpus is 30 docs; plain BM25 (with unicode-fold + accent-strip + lowercase normalization) may be sufficient. Hybrid (BM25 + multilingual embeddings + RRF) is a documented level-up, gated on eval failure *and* a conversation with the project owner — never auto-promoted. See `docs/ARCHITECTURES.md` § "Classic hybrid retrieval pipeline" for the corpus-growth and audience-expansion reasoning.
4. **No prior assistant answers in the source-of-truth context.** Each turn runs fresh tool calls. Prior conversation is used only to rewrite the current question.
5. **The agent loop is bounded.** Max 5 tool calls, `reasoning_effort="low"` on the default model, no final answer until at least one search has run. Enforced by the orchestrator, not the prompt.
6. **Tests run without an LLM by default.** LLM-in-the-loop is isolated to the eval pipeline. Unit + integration CI never burns provider tokens.
7. **Token usage is visible.** Every LLM call returns a `usage` block; the orchestrator stamps every step with IDs; the HTTP response includes per-step usage in `debug` and token totals in `usage_summary`.

## In scope for v1

- Markdown ingestion → SQLite passage store with stable IDs. **Triggered via `POST /admin/ingest`**, not a CLI.
- `LLMProvider` and `EmbeddingProvider` abstractions; **OpenAI adapter** (`gpt-5.5` by default; `text-embedding-3-large` ships in the adapter even though current retrieval doesn't use embeddings — keeps the adapter complete). The Anthropic adapter is designed but not implemented in v1 — `app/providers/factory.py` raises `ProviderError("anthropic adapter is not yet implemented")`; portability is proved by the protocol shape in `app/providers/base.py`, not by a second live adapter.
- Four read-only tools: `list_documents`, `read_document_outline`, `search_convictions` (BM25-only at v1), `read_passage`
- Bounded agent loop with structured-JSON output
- Deterministic offset resolver: turns each cited quote into `(start, end)` offsets in the passage, drops the literal text; non-anchoring citations survive without a highlight
- Disclaimer + audit log + token usage on every response (PT / EN / **ES** disclaimers — Spanish users may ask in Spanish even though the corpus is PT/EN)
- `POST /chat` endpoint
- Lightweight React frontend (Vite + React + TypeScript + Tailwind; built to static files and mounted under FastAPI); citation popup with the cited region highlighted in the passage
- Eval suite (~30 hand-written Q/A) with **anchor rate** (% of citations that resolved) as headline metric

## Out of scope for v1 (designed, not built)

- PDF / Excel uploads (the challenge bonus)
- **Postgres + pgvector** — SQLite ships v1; Postgres is the documented level-up
- **Hybrid retrieval (BM25 + dense + RRF)** — BM25 ships v1; hybrid is the documented level-up
- Cross-encoder reranker inside `search_convictions` (further level-up beyond hybrid)
- Anthropic Citations API optimization inside the Anthropic adapter

See `docs/ARCHITECTURES.md` § "Not implemented in this version" for the design.


## Architecture — Strict Layer Separation

```
Router → Service → Repository (never skip layers)
```

- **`app/api/`** — Route handlers. Thin controllers; no business logic. Maps domain exceptions to HTTP responses via handlers registered in `app/main.py`. Routers are the only layer that knows about HTTP.
- **`app/services/`** — Business logic. Services raise domain exceptions (defined in `app/errors.py`); they NEVER raise `HTTPException` or reference HTTP status codes.
- **`app/services/parser/`** — Pure markdown → `Passage` transformation. Sync; called from `app/services/ingest.py`.
- **`app/repositories/`** — Data access. **All SQLAlchemy queries live here.** Module-level async functions take an `AsyncSession`; transaction control belongs to the caller (services wrap writes in `async with session.begin(): …`).
- **`app/models/`** — SQLAlchemy ORM models. `Base` (DeclarativeBase) + per-table modules.
- **`app/schemas/`** — Pydantic request/response schemas. `ConfigDict(from_attributes=True)` on schemas that mirror ORM rows.
- **`app/errors.py`** — Domain exceptions (`DomainError`, `IngestError`, `PassageNotFoundError`, `DocumentNotFoundError`, …); mapped to HTTP at the API boundary by handlers in `app/main.py`.
- **`app/agent/`** — Agent loop, tool dispatch, audit, and the read-only tools it can call (`app/agent/tools/`). Tools are pure functions over the repository contract; storage-agnostic by rule. DI via `ToolContext`. Hand-written JSON-schema dicts. Single `TOOLS` registry. See `docs/ARCHITECTURES.md` § "Tools layer".
- **`app/retrieval/`** — `Retriever` Protocol + interchangeable strategies (BM25 today, hybrid as documented level-up). Top-level (not under `services/`) because it mirrors the `app/providers/` shape: one `base.py` contract, N adapters, lifecycle owned by the FastAPI app (built at lifespan, rebuilt at admin ingest). Services orchestrate; retrieval is consumed via `ToolContext`.
- **`alembic/`** — Schema-of-record. Imperative migrations (op.create_table / op.execute); autogenerate is intentionally disabled until every table has an ORM model.

### Backend layout

```
app/
  errors.py           # domain exceptions; mapped to HTTP at the API boundary
  main.py             # lifespan (engine setup + auto-ingest), router include, exception handlers
  config/
    settings.py       # Settings class — only place env-var loading happens; re-exported from __init__
    db.py             # async engine + session factory + sync alembic migrate (no SQL — engine plumbing)
  api/
    health.py         # GET /health
    admin.py          # POST /api/admin/ingest
    chat.py           # POST /api/chat
    chat_history.py   # GET /api/chat/conversations (user-facing list + load)
    config.py         # GET /api/config — surfaces the server-selected chat model
    auth.py           # X-Chat-Token / X-Admin-Token validation
    deps.py           # FastAPI Depends factories (provider DI; test patch point)
    schemas.py        # HTTP request/response Pydantic models (ChatRequest, ChatResponse, …)
  services/
    ingest.py         # parser → repo orchestration
    audit.py          # persist_question — serialize agent steps into audit_log rows
    chat.py           # one /chat turn: IDs → agent → response wrapping → audit
    chat_history.py   # reconstruct ConversationMessage / ChatCitation / UsageSummary from audit_log rows
    disclaimer.py     # localized disclaimer strings (PT / EN / ES)
    wrap_response.py  # AgentResult → wire response + audit summary
    parser/           # pure: markdown -> passages; dispatch by extension in registry.py
  repositories/
    passages.py       # SQLAlchemy 2.x async repo for passages
    audit.py          # audit_log access (insert_many, fetch_by_*)
  models/
    base.py           # DeclarativeBase
    passage.py        # PassageORM
    audit.py          # AuditLogORM
  schemas/
    passage.py        # Pydantic Passage / DocSummary / Heading / DocumentOutline / PassageHit
    ingest.py         # Pydantic IngestResponse
  providers/          # *** SINGLE POINT OF LLM INTERACTION ***
    base.py           # LLMProvider + EmbeddingProvider Protocols, TokenUsage
    factory.py        # get_llm_provider() / get_embedding_provider() — dispatch on settings
    openai.py         # OpenAI adapter
    stub.py           # StubLLM / StubEmbedder for CI (no provider tokens burned)
    text_repair.py    # post-hoc unicode-escape fixer (gpt-5-mini quirk)
  retrieval/          # Retriever protocol + adapters (BM25 today, hybrid later)
                      # base.py contract; registry.py explicit dispatch; snippet.py shared helper
  agent/              # bounded loop, rewrite, dispatch, audit, dedupe
    loop.py           # gather → act → resolve orchestrator (max-tool-calls, ≥1-search-before-answer)
    rewrite.py        # multi-turn question rewrite + language detection
    tool_dispatch.py  # executes one tool call via TOOLS registry
    schemas.py        # AgentOutput, AnswerOutput, ClarifyingQuestionOutput, StepRecord
    audit.py          # step recording + resolver adapter
    dedupe.py         # collapse duplicate citations by passage_id, remap [N] markers
    prompts/          # system.md, rewrite.md
    resolver/         # deterministic substring → (start, end); literal quote dropped
    tools/            # read-only tools (storage-agnostic, ToolContext DI)
                      # list_documents, read_document_outline, read_passage, search_convictions
alembic/
  env.py
  script.py.mako
  versions/
    0001_initial_schema.py    # passages, audit_log
```

### Hard rules (CI-greppable)

These rules are non-negotiable. Code review (and CI grep) enforces them.

1. **No code outside `app/repositories/` runs SQL.** Services, the agent, tools, tests — everyone goes through repository functions.
2. **No code outside `app/providers/` ever imports `openai`, `anthropic`, or any provider SDK.** Including tests.
3. **No code outside `app/config/` calls `os.getenv`.** All settings flow through `config.settings` (defined in `app/config/__init__.py`).
4. **No business logic in `app/api/`.** Routers parse request → call service → wrap response.
5. **Services and repositories NEVER raise `HTTPException`** or reference HTTP status codes. They raise domain exceptions; the API layer maps them.

### CRITICAL — SQLAlchemy 2.x async rules

- ALWAYS use `AsyncSession` (never sync `Session`)
- ALWAYS use `select()` style: `select(PassageORM).where(PassageORM.id == id)`
- ALWAYS use the `aiosqlite` driver: `sqlite+aiosqlite:///path`
- ALWAYS use `selectinload()` or `joinedload()` for relationships (rule applies as soon as one lands)
- NEVER use legacy `query()` style: `session.query(...)`
- NEVER call sync methods on an `AsyncSession`

### CRITICAL — Pydantic v2 rules

- ALWAYS use `ConfigDict(from_attributes=True)` on schemas that mirror ORM rows
- ALWAYS use `@field_validator` (never `@validator`)
- ALWAYS use `@model_validator` (never `@root_validator`)
- ALWAYS use `.model_dump()` (never `.dict()`)
- ALWAYS use `.model_dump_json()` (never `.json()`)
- NEVER import from `pydantic.v1`

### CRITICAL — Error handling & HTTP rules

- Services and repositories NEVER raise `HTTPException`
- Services raise domain exceptions defined in `app/errors.py` (subclasses of `DomainError`)
- The API layer maps domain exceptions to HTTP responses via handlers registered in `app/main.py`
- Routers are the only layer that knows about HTTP — status codes, headers, response formatting stay in `app/api/`
- ALWAYS use `async def` for endpoints
- ALWAYS use `Depends()` for dependency injection (DB sessions, future auth)
- ALWAYS return Pydantic schemas, never raw ORM objects or dicts
- NEVER use `@app.on_event()` — use `lifespan` context managers (already in `app/main.py`)

The `LLMProvider` and `EmbeddingProvider` protocols are the *only* contract above provider adapters. `StubProvider` is what every CI test uses — the test suite never burns provider tokens.

### Frontend layout

```
frontend/src/
  lib/api.ts       # *** SINGLE POINT OF BACKEND INTERACTION ***
  lib/types.ts     # mirrored from backend Pydantic models
  components/      # generic UI primitives
  features/chat/   # message list, composer, citation rendering
  features/debug/  # debug drawer
```

- **No `fetch` or `axios` outside `lib/api.ts`.** ESLint rule enforced.
- **No backend types redefined inline in components.** They live in `lib/types.ts`.

## Commit conventions

- **Subject under 150 characters.** No body. No `Co-Authored-By:` trailer.
- Imperative voice, no trailing period.
- One concept per commit; if the subject wants to say "and", split.

## Conventions for working in this repo

- Don't add new dependencies without a reason that holds up to "could a smart reader find this overkill?"
- Don't add abstraction layers for hypothetical future providers / formats. The provider interface is justified because portability is an explicit requirement; nothing else gets that pass.
- Don't write comments that restate the code. Reserve comments for non-obvious *why* (a resolver choice, an unusual loop bound, etc.).
- Pure functions where possible (parser, tools, resolver). Pure functions are testable; mocks are not.
- The eval suite's headline metric is **anchor rate** (% of citations whose quotes resolved to offsets). Other metrics complement; don't replace it.
