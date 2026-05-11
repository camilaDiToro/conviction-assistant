---
title: Decade AI Challenge
emoji: 📚
colorFrom: blue
colorTo: purple
sdk: docker
app_port: 7860
pinned: false
---

# Decade AI Challenge

A conversational assistant grounded on Decade's investment conviction
documents (PT / EN corpus; ES queries supported). The interview framing
in one sentence: **deterministic offset-based provenance as the
grounding guarantee — every cited quote resolves to a `(start, end)`
region of the cited passage, and the UI shows the user exactly what was
cited.** Paired with a constrained agentic harness whose discipline is
inspired by Claude Code (small read-only tool surface, bounded
gather → act loop). No provider's native Citations API matches this
guarantee.

- Brief: [`AI_CHALLENGE.md`](AI_CHALLENGE.md)
- Architecture & design: [`docs/ARCHITECTURES.md`](docs/ARCHITECTURES.md), [`CLAUDE.md`](CLAUDE.md)
- Eval suite: [`evals/README.md`](evals/README.md), [`evals/RAGAS_USAGE.md`](evals/RAGAS_USAGE.md)

## Stack

Python 3.12 · FastAPI · SQLAlchemy 2.x async (aiosqlite) · Pydantic v2 ·
Alembic · uv · pytest · ruff · mypy. Frontend: Vite + React + TypeScript
+ Tailwind. LLM provider: OpenAI (gpt-5 family) via a provider-agnostic
adapter (`app/providers/`); Anthropic adapter is documented as future
work and is out of scope for this iteration.

## Quickstart

```sh
# 1. Backend dependencies
uv sync

# 2. .env — at minimum set the access tokens and (if running the agent for real) OpenAI
cp .env.example .env
# Edit .env: CHAT_ACCESS_TOKEN, ADMIN_TOKEN, OPENAI_API_KEY

# 3. Ingest the corpus
uv run uvicorn app.main:app --reload
# in another shell:
curl -X POST http://localhost:8000/api/admin/ingest -H "X-Admin-Token: $ADMIN_TOKEN"

# 4. Frontend (separate process — Vite dev server proxies /api/* to FastAPI)
cd frontend && npm install && npm run dev
# open http://localhost:5173 — paste your CHAT_ACCESS_TOKEN at the gate
```

## Architecture in one paragraph

A bounded tool-using agent (max 5 tool calls per question, `≥ 1`
search before any final answer, structured JSON output) gathers
evidence from a SQLite passage store via four read-only tools
(`list_documents`, `read_document_outline`, `search_convictions`,
`read_passage`). The model emits citations as `{passage_id, quote}`
pairs; before the wire response is built, a deterministic offset
resolver turns each verbatim quote into `(start, end)` offsets in the
cited passage and drops the literal text. The UI renders the cited
passage with that region highlighted. Citations whose quotes do not
anchor survive without a highlight — the popup still shows the source
passage, so the user can verify even imperfect citations. Multi-turn
conversation memory is quarantined to a rewrite stage: prior assistant
text never re-enters the grounded retrieval path.

Full details, the alternatives considered and rejected, and the
production-vs-simplified tier breakdown live in `docs/ARCHITECTURES.md`.

## Running the chat

```sh
# Backend
uv run uvicorn app.main:app --reload

# Frontend (separate shell)
cd frontend && npm run dev
```

Visit `http://localhost:5173/chat`, paste the chat token, ask in PT/EN/ES.
The chat UI shows the server-selected model in the header; `/chat` itself
has one behavior, configured by the backend.

## Testing

```sh
uv run pytest                       # default suite; never burns provider tokens
uv run ruff check . && uv run mypy . # lint + types
cd frontend && npm run build        # frontend type-check + bundle
```

## Eval suite

Hand-authored 30-question golden set + four deterministic metrics +
Ragas-decorator-based runner. Headline metric: **anchor rate** — what
fraction of cited quotes resolved to an offset region.

```sh
# Smoke (3 questions, balanced across buckets):
uv run python -m evals.run --reasoning low --limit 3

# Full 30 questions:
uv run python -m evals.run --reasoning medium

# Compare two runs (e.g. low vs medium):
uv run python -m evals.compare evals/results/run_a.csv evals/results/run_b.csv
```

The runner is opt-in (burns real OpenAI tokens). `pytest -m eval` runs
the eval test layer; default `pytest` skips it. See
[`evals/README.md`](evals/README.md) for metric definitions and golden
set structure, and [`evals/RAGAS_USAGE.md`](evals/RAGAS_USAGE.md) for
which Ragas features the suite uses and which it deliberately skips
(no LLM-as-judge — deterministic metrics only).

A `--with-judge` flag is reserved for adding Ragas's LLM-judge metrics
(Faithfulness, AnswerRelevancy) later; not wired in this iteration.

## Operational endpoints

| Endpoint | Auth | Purpose |
|---|---|---|
| `POST /api/admin/ingest` | `X-Admin-Token` | Parse `convictions/` into SQLite |
| `POST /api/chat` | `X-Chat-Token` | Run one agent turn |
| `GET  /api/config` | `X-Chat-Token` | Return the server-selected chat model |
| `GET  /api/chat/conversations` | `X-Chat-Token` | List the caller's conversations (sidebar) |
| `GET  /api/admin/conversations/{id}` | `X-Admin-Token` | Full trace of a conversation |
| `GET  /health` | — | Liveness check |

## Where things live

```
app/
  api/             # FastAPI routers — thin controllers, no business logic
  services/        # business logic; raises domain exceptions (never HTTPException)
  repositories/    # ALL SQLAlchemy queries; module-level async functions
  models/          # SQLAlchemy ORM
  schemas/         # Pydantic request/response shapes
  providers/       # LLMProvider + EmbeddingProvider; only place that imports openai
  retrieval/       # Retriever protocol + BM25 adapter; lifecycle owned by app lifespan
  agent/           # Bounded loop, rewrite stage, structured-output schemas
    tools/         # The four read-only tools the agent can call
    resolver/      # Deterministic substring → (start, end) offset resolver
    prompts/       # System + rewrite prompts (markdown)
  config/          # Settings + DB engine plumbing — only place that calls os.getenv
alembic/           # Schema-of-record migrations
convictions/       # The 30-doc corpus
docs/              # ARCHITECTURES, ASSUMPTIONS, deploy, testing, scale notes
evals/             # golden set + runner + metrics + comparator
frontend/          # Vite + React + Tailwind chat UI + architecture explainer
tests/             # Mirrors app/ + an `eval/` layer (skipped by default)
```

CI-greppable layering rules:

1. No code outside `app/repositories/` runs SQL.
2. No code outside `app/providers/` imports `openai` or another provider SDK.
3. No code outside `app/config/` calls `os.getenv`.
4. No business logic in `app/api/`.
5. Services and repositories never raise `HTTPException`; they raise domain exceptions mapped to HTTP at the API boundary.
