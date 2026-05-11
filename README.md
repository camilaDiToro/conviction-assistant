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
Per-request **overrides** (model, reasoning effort, max tool calls, max
output tokens) are available from the settings gear in the chat header
and persist in `localStorage`; effective values are visible per-step in
the debug drawer.

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
# Smoke (3 questions, balanced across buckets, ~$0.05):
uv run python -m evals.run --reasoning low --limit 3

# Full 30 questions (~$1-3 at gpt-5 medium):
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

## Refreshing model prices

Per-call USD cost is computed in `app/services/cost.py` from
`app/providers/_model_prices.json`, a trimmed copy of LiteLLM's
[`model_prices_and_context_window.json`](https://github.com/BerriAI/litellm/blob/main/model_prices_and_context_window.json)
(the de-facto industry source for LLM pricing data). Prices are **per
token**, not per million — multiply token counts directly.

```sh
uv run python scripts/refresh_prices.py
git diff app/providers/_model_prices.json
# review the diff — these are real money numbers
git add app/providers/_model_prices.json
git commit -m "refresh model prices from upstream"
```

The `WANTED_MODELS` list in the script pins what gets refreshed; it must
cover every model in `settings.allowed_models` (the `/chat` override
whitelist) plus the embedding models. When a wanted model isn't in
upstream yet (a just-announced flagship like the first `gpt-5.5`
release), the script **warns and preserves the existing manual entry**
— confirm those numbers against
[OpenAI's pricing page](https://openai.com/api/pricing/) by hand and
note them with `"_note": "approximate — confirm..."` so future readers
know they aren't upstream-verified.

Refresh before any release or eval run; **don't** refresh mid-eval —
price drift across runs muddies cost comparisons. To add a new model:
append to `WANTED_MODELS`, run the script, add to `settings.allowed_models`
(if it should be selectable via `/chat` overrides). We vendor the JSON
instead of importing `litellm` because the package ships a large
abstraction layer + dozens of transitive deps for one piece of data.

## Production-grade vs deliberately simplified

This project ships two tiers of code; reviewers should be able to tell
at a glance which one any file belongs to.

**Production-grade — built right:**

- Provider abstraction (`LLMProvider` / `EmbeddingProvider`, single-LLM-point rule)
- Offset resolver — deterministic substring → `(start, end)` mapping; the literal quote is dropped before the response is built
- Agent loop bounds (max 5 tool calls; `≥ 1` search before answer; tools dropped on forced-final turn)
- Audit log + 3-granularity cost tracking (per step / per question / per conversation)
- Response contract (deterministic disclaimer, language mirroring, schema-validated)
- Tool surface (read-only, hand-written JSON schemas, pure-function tests)
- Layering rules (Router → Service → Repository; CI-greppable — see `CLAUDE.md`)

**Deliberately simplified — well-known production paths exist; documented as level-up, not built:**

- SQLite + BM25-only retrieval (vs Postgres + pgvector + FTS; the hybrid path is documented as a level-up in `docs/ARCHITECTURES.md`)
- In-process FastAPI (vs Docker / k8s / multi-replica — see `docs/DEPLOYMENT.md`)
- Two-token auth only (chat + admin); no JWT/OAuth, no per-user identity, no rate limit
- File-based settings (vs secrets manager)
- 30 hand-written eval questions, deterministic metrics only (vs auto-generated bank + LLM-judge dashboard)
- No streaming (single sync `/chat`; SSE is out of scope)
- Single LLM provider (OpenAI; Anthropic adapter slot documented, not built)

Each level-up is described in the step where it would land. Promotion
from "simplified" to "production-grade" is a conversation, not
auto-triggered by the implementer.

## Operational endpoints

| Endpoint | Auth | Purpose |
|---|---|---|
| `POST /api/admin/ingest` | `X-Admin-Token` | Parse `convictions/` into SQLite |
| `POST /api/chat` | `X-Chat-Token` | Run one agent turn; accepts optional `overrides` body |
| `GET  /api/config` | `X-Chat-Token` | Server defaults + allowed override values for the settings UI |
| `GET  /api/chat/conversations` | `X-Chat-Token` | List the caller's conversations (sidebar) |
| `GET  /api/admin/conversations/{id}` | `X-Admin-Token` | Full trace of a conversation |
| `GET  /api/admin/conversations/{id}/cost` | `X-Admin-Token` | Per-question cost rollup |
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
  tools/           # The four read-only tools the agent can call
  agent/           # Bounded loop, rewrite stage, structured-output schemas
  config/          # Settings + DB engine plumbing — only place that calls os.getenv
  verifier/        # Substring resolution policy (NFC, smart-quote folding, etc.)
alembic/           # Schema-of-record migrations
convictions/       # The 30-doc corpus
docs/              # ARCHITECTURES, scaling notes, deployment, testing
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
