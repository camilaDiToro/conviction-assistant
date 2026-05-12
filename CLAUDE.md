# CLAUDE.md — Decade AI Challenge


## What this project is

A conversational AI assistant strictly grounded on Decade's investment conviction documents. The challenge brief is in `AI_CHALLENGE.md`. The corpus is in `convictions/` (30 markdown files, mixed Portuguese/English, expected to grow).

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
## RULES 

### 🔴 Rule A — General knowledge MUST be marked very, very clearly

The assistant **may** use general knowledge when the convictions don't cover a topic, but it **MUST be made very, very clear** to the user. Specifically:

- **Always prefer a real conviction reference**, even if it mentions the topic only tangentially. The citation must include passage ID + document title + heading path + exact quote, so the analyst can see *where* the convictions mention it.
- **Only fall back to general knowledge when no conviction touches the topic at all.**
- General-knowledge text **must be marked unambiguously** (dedicated section heading like "**Not from Decade convictions — general knowledge:**", or an equivalent visual prefix).
- **Never interleave** general-knowledge claims with conviction-grounded claims in the same paragraph without a clear delimiter.
- The structured response carries `general_knowledge_used: true` and a separate `general_knowledge_section` field.

### 🔴 Rule B — Conflicting convictions MUST be surfaced

When two or more convictions contradict each other on a topic:

- **Cite all sides.** Never silently pick one.
- **State explicitly that the convictions disagree.**
- The analyst makes the judgment call; the assistant does not pretend consensus exists.

---

## Out of scope for v1 (designed, not built)

- PDF / Excel uploads (the challenge bonus)

See `docs/ARCHITECTURES.md` § "Not implemented in this version" for the design.


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


1. **No code outside `app/repositories/` runs SQL.** Services, the agent, tools, tests — everyone goes through repository functions.
2. **No code outside `app/providers/` ever imports `openai`, `anthropic`, or any provider SDK.** Including tests.
3. **No code outside `app/config/` calls `os.getenv`.** All settings flow through `config.settings` (defined in `app/config/__init__.py`).
4. **No business logic in `app/api/`.** Routers parse request → call service → wrap response.
5. **Services and repositories NEVER raise `HTTPException`** or reference HTTP status codes. They raise domain exceptions; the API layer maps them.


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
