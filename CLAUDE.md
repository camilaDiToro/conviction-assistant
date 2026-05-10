# CLAUDE.md — Decade AI Challenge

Index for future Claude sessions working on this project. Read this first; follow the pointers.

## What this project is

A conversational AI assistant strictly grounded on Decade's investment conviction documents. The challenge brief is in `AI_CHALLENGE.md`. The corpus is in `convictions/` (30 markdown files, mixed Portuguese/English, expected to grow).

**One-line framing for the interview:** *a deterministic substring verifier as the grounding guarantee — paired with a constrained agentic harness (small read-only tool surface + bounded gather→act→verify loop) whose discipline is inspired by Claude Code. No provider's Citations API matches the verifier's guarantee.*

The architecture is a **deterministic citation verifier + constrained tool-using agent**: the model gets read-only tools over a passage store and produces structured answers; every cited quote is substring-verified against the source before it reaches the user. Retry-with-feedback on first failure; strip-claim on second.

**A note on the Claude Code analogy.** We adopt Claude Code's two load-bearing ideas — a small read-only tool surface and the gather→act→verify loop — but we keep a deterministic retrieval index (BM25, sparse) instead of going full grep-in-the-loop. The corpus is natural-language PT/EN prose, not source code: grep alone misses paraphrase, and at 30 documents the per-turn latency win for the user dominates the token-cost win the agent would get from navigating outlines in real time. A purer Claude Code interpretation (drop `search_convictions`, give the agent only `list_documents` + `read_document_outline` + `read_passage`) was considered and rejected on those grounds. BM25-vs-hybrid is a tactical level-up gated on eval (see `docs/reports/b6-*.md`); the verifier is the architectural commitment.

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
| Trigger ingest | `curl -X POST http://localhost:8000/admin/ingest` |

## Project framing — production-grade vs deliberately simplified

This project ships **two tiers of code**, deliberately. A reviewer should be able to tell at a glance which tier any file belongs to. Optimize for code quality, clarity, and defensibility under interview questions — and pick the right tier for each piece.

**Production-grade (built right; will survive a deep-dive):**
- Provider abstraction (`LLMProvider` / `EmbeddingProvider`, single-LLM-point rule)
- Citation verifier (deterministic, exhaustively tested, retry-with-feedback)
- Agent loop bounds (max 5 tool calls, ≥ 1 search before answer, `reasoning_effort="low"` on gpt-5 — see `docs/MODEL_CONFIG.md`; determinism enforced by the verifier, not by `temperature`)
- Audit log + cost tracking (3 granularities)
- Response contract (deterministic disclaimer, language mirroring, schema-validated)
- Tool surface (read-only, JSON-schema-defined, pure-function tests)
- Layering rules (CI-greppable; see § "Layering & single-LLM-point" below)

**Deliberately simplified (well-known production paths exist; documented as level-up, not built):**
- SQLite + Python BM25 (vs Postgres + pgvector + FTS — see ROADMAP B3 / B6 level-ups)
- In-process FastAPI (vs Docker / k8s / multi-replica — see `docs/DEPLOYMENT.md`)
- No auth, no rate limit, no SSE streaming (single sync `/chat` — see ROADMAP B9)
- File-based settings (vs secrets manager)
- ~30 hand-written eval questions (vs auto-generated bank + LLM-judge dashboard — see ROADMAP B10)

Each level-up is documented in the step where it would land, so a reviewer can see we knew what we were skipping and why. **Promotion from "simplified" to "production-grade" is a conversation, not auto-triggered by the implementer.** See `docs/ASSUMPTIONS.md` § "Operational" for the longer framing.

## Where to read what

| File | Purpose |
|---|---|
| `AI_CHALLENGE.md` | The challenge brief from Decade. The requirements live here. |
| `docs/ROADMAP.md` | **Multi-session step-by-step build plan.** Read this at the start of every implementation session. Update between sessions (check off `- [x]`, note deviations). |
| `docs/ARCHITECTURES.md` | **The chosen architecture.** Tool surface, agent loop, verifier, what's *not* implemented in this version, alternatives that were considered and rejected, eval-driven implementation order. |
| `docs/TESTING.md` | Testing strategy. Layer-by-layer test plan, faithfulness eval suite, CI tiers. Confirms the architecture is testable by construction. |
| `docs/QUESTIONS.md` | Open questions to ask Decade that could change the design. |
| `docs/ASSUMPTIONS.md` | Confirmed assumptions from the project owner. Read before making decisions. |
| `docs/RETRIEVAL_SCALE.md` | Why each corpus size implies a different retrieval stack. |
| `docs/SCALING.md` | What changes in the architecture as concurrent-user count grows. |
| `docs/DEPLOYMENT.md` | Concrete deploy plan: tech stack, hosting choice, architecture diagram, key decisions, scale path. |
| `docs/PRICING.md` | How we keep up-to-date model prices without a runtime pricing library: vendored JSON from LiteLLM upstream + `scripts/refresh_prices.py`. Covers why we rejected LiteLLM-the-package and `tokencost`. |
| `docs/MODEL_CONFIG.md` | Why each gpt-5 tuning knob (`reasoning_effort`, `verbosity`, `max_output_tokens`, timeout) has the value it does for this use case. |

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
- **Indicate which conviction is newer**, using each document's `Updated:` date (parsed from the markdown header).
- The analyst makes the judgment call; the assistant does not pretend consensus exists.

This requires the parser to extract `Updated:` dates from document headers and surface them in tool results (`search_convictions`, `read_passage`).

---

## Other design principles (do not violate)

1. **The agent finds evidence; the verifier enforces grounding.** These are separate responsibilities. Don't move grounding logic into the prompt or rely on the model to self-verify.
2. **No provider-native grounding feature is the architecture.** They live behind adapters as optimizations only. The contract above the adapter is identical across Anthropic, OpenAI, Gemini.
3. **BM25-only is the v1 retrieval baseline.** The corpus is 30 docs; plain BM25 (with unicode-fold + accent-strip + lowercase normalization) may be sufficient. Hybrid (BM25 + multilingual embeddings + RRF) is the documented level-up under ROADMAP B6, gated on eval failure *and* a conversation with the project owner — never auto-promoted. See `docs/RETRIEVAL_SCALE.md` for the per-corpus-size reasoning.
4. **No prior assistant answers in the source-of-truth context.** Each turn runs fresh tool calls. Prior conversation is used only to rewrite the current question.
5. **The agent loop is bounded.** Max 5 tool calls, `reasoning_effort="low"` on gpt-5, no final answer until at least one search has run. Enforced by the orchestrator, not the prompt.
6. **Tests run without an LLM by default.** LLM-in-the-loop is isolated to the eval pipeline. Unit + integration CI never burns provider tokens.
7. **Cost tracking is mandatory at three granularities** — per step, per question, per conversation. Every LLM call returns a `usage` block; the orchestrator stamps every step with IDs; the HTTP response includes per-step usage in `debug` and a `usage_summary` at the top. See `docs/ASSUMPTIONS.md` § "Cost tracking — REQUIRED" for the schema.

## In scope for v1

- Markdown ingestion → SQLite passage store with stable IDs (incl. `Updated:` date extraction). **Triggered via `POST /admin/ingest`**, not a CLI.
- `LLMProvider` and `EmbeddingProvider` abstractions; **OpenAI adapter first** (`gpt-5`; `text-embedding-3-large` ships in the adapter even though B6 doesn't use embeddings — keeps the adapter complete), Anthropic adapter second (portability proof)
- Four read-only tools: `list_documents`, `read_document_outline`, `search_convictions` (BM25-only at v1), `read_passage`
- Bounded agent loop with structured-JSON output
- Deterministic citation verifier with retry-once-with-feedback (built **before** the agent loop so every later step measures verifier pass rate)
- Disclaimer + audit log + cost tracking on every response (PT / EN / **ES** disclaimers — Spanish users may ask in Spanish even though the corpus is PT/EN)
- `POST /chat` endpoint
- Lightweight React frontend (Vite + React + TypeScript + Tailwind; built to static files and mounted under FastAPI)
- Eval suite (~30 hand-written Q/A) with verifier pass rate as headline metric

## Out of scope for v1 (designed, not built)

- PDF / Excel uploads (the challenge bonus)
- **Postgres + pgvector** — SQLite ships v1; Postgres is the documented level-up under ROADMAP B3
- **Hybrid retrieval (BM25 + dense + RRF)** — BM25 ships v1; hybrid is the documented level-up under ROADMAP B6
- Cross-encoder reranker inside `search_convictions` (further level-up beyond hybrid)
- Anthropic Citations API optimization inside the Anthropic adapter

See `docs/ARCHITECTURES.md` § "Not implemented in this version" and `docs/ROADMAP.md` per-step "Level-up path" subsections for the design.

## Implementation order

Documented in `docs/ARCHITECTURES.md` § "Implementation order (eval-driven)". Each step should pass the eval before moving to the next.

## Design decisions explicitly considered and rejected

Documented so future sessions don't re-litigate them.

- **`confidence: high|medium|low` field on the response.** Adds an unverifiable signal — the model self-reports confidence, which is exactly the kind of thing we don't want to trust. The verifier pass/fail is a stronger and more honest signal. Rejected.
- **`/retrieve` endpoint alongside `/chat`** (returns retrieved evidence without generation). Genuinely useful for the demo; not required for v1. May be added if time allows.
- **`/eval` endpoint** for running the eval suite via HTTP. Replaced by the `pytest -m eval` suite documented in `docs/TESTING.md` — better dev ergonomics, no production endpoint to secure.
- **Lightweight evidence-selector model inside `search_convictions`.** A second small model that picks the best 4–8 of the fused top-30. Correct technique at thousands+ docs; premature for v1. See `docs/RETRIEVAL_SCALE.md`.
- **Cross-encoder reranker** inside `search_convictions`. Adds a model + latency. Justified at hundreds+ docs; gated on a hybrid-retrieval failure that we don't yet have evidence for. See `docs/RETRIEVAL_SCALE.md`.
- **Hybrid retrieval (BM25 + dense + RRF) as the v1 baseline.** Reconsidered after design pushback: at 30 docs, BM25 alone may suffice; building two retrieval paths + fusion before knowing whether one path works is premature. Hybrid is now the *documented level-up* under ROADMAP B6, gated on a cross-language eval failure plus a conversation. The RRF + multilingual-embedding design from earlier still applies if/when promoted.
- **Postgres + pgvector as the v1 store.** Reconsidered after design pushback: at 30 docs and a single-process FastAPI demo, SQLite + the BM25 library covers everything. The repository contract in `app/repositories/` is the swap point; level-up to Postgres is documented under ROADMAP B3.
- **Sync sqlite3 + module-level repository functions taking `sqlite3.Connection`.** First B3 implementation. Reconsidered before B4: migrating to **SQLAlchemy 2.x async** (AsyncSession + `select()` + aiosqlite) to align with the project stack-conventions (Router→Service→Repository, async-first FastAPI ecosystem) and to give the repository a typed, stack-standard swap surface. The original sync version was correct but inconsistent with the chosen stack; refactored before later steps build on the wrong base.
- **`python -m app.ingest` CLI.** First B3 surface. Reconsidered: replaced with `POST /admin/ingest` so the admin surface is consistent (HTTP-only) and the lifespan-managed engine is reused. The parser dev CLI at `app/services/parser/cli.py` stays — it's a developer-ergonomics tool, not a user-facing surface.

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
- **`app/tools/`** — Read-only tools the agent can call. Pure functions over the repository contract; storage-agnostic by rule. DI via `ToolContext`. Hand-written JSON-schema dicts. Single `TOOLS` registry. See `docs/ARCHITECTURES.md` § "Tools layer" and `docs/b5-decisions.md`.
- **`alembic/`** — Schema-of-record. Imperative migrations (op.create_table / op.execute); autogenerate is intentionally disabled until every table has an ORM model (audit_log lands in B9).

### Backend layout

```
app/
  config/
    __init__.py       # Settings class + settings instance — only place env-var loading happens
    db.py             # async engine + session factory + sync alembic migrate (no SQL — engine plumbing only)
  errors.py           # domain exceptions; mapped to HTTP at the API boundary
  main.py             # lifespan (engine setup), router include, exception handlers
  api/
    health.py         # GET /health
    admin.py          # POST /admin/ingest (and future admin endpoints)
    # later: chat.py (B9), …
  services/
    ingest.py         # parser → repo orchestration
    parser/           # pure: markdown -> passages; no I/O beyond file reads
    # later: agent/, verifier/, retrieval/, …
  repositories/
    passages.py       # SQLAlchemy 2.x async repo for passages
    introspection.py  # list_tables / list_views — schema diagnostics (uses raw text() SQL)
    # later: audit.py (when B9 lands)
  models/
    base.py           # DeclarativeBase
    passage.py        # PassageORM
  schemas/
    passage.py        # Pydantic Passage / DocSummary / Heading / DocumentOutline
    ingest.py         # Pydantic IngestResponse
  providers/          # B4: LLMProvider + EmbeddingProvider protocols + adapters
                      # *** SINGLE POINT OF LLM INTERACTION ***
  tools/              # B5: read-only tools the agent calls (storage-agnostic, ToolContext DI)
                      # list_documents, read_document_outline, read_passage; +search_convictions in B6
alembic/
  env.py
  script.py.mako
  versions/
    0001_initial_schema.py    # passages, audit_log, cost_log view
```

### Hard rules (CI-greppable)

These rules are non-negotiable. Code review (and CI grep) enforces them.

1. **No code outside `app/repositories/` runs SQL.** Services, the agent, tools, tests — everyone goes through repository functions.
2. **No code outside `app/providers/` ever imports `openai`, `anthropic`, or any provider SDK.** Including tests. (`app/providers/` lands in B4.)
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

The `LLMProvider` and `EmbeddingProvider` protocols are the *only* contract above provider adapters. `StubProvider` ships in B4 and is what every CI test uses — the test suite never burns provider tokens.

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
- Don't write comments that restate the code. Reserve comments for non-obvious *why* (a verifier normalization choice, an unusual loop bound, etc.).
- Pure functions where possible (parser, tools, verifier). Pure functions are testable; mocks are not.
- The eval suite's headline metric is **verifier pass rate**. Other metrics complement; don't replace it.
