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
- Eval suite: [`evals/README.md`](evals/README.md)

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

## Testing

```sh
uv run pytest                       # default suite; never burns provider tokens
uv run ruff check . && uv run mypy . # lint + types
cd frontend && npm run build        # frontend type-check + bundle
```

## Eval suite

Hand-authored 34-question golden set. The code runner is deterministic:
it records citation anchoring, passage precision/recall, refusal and
clarify correctness, Rule A / Rule B checks, language match, token
usage, tool calls, and duration. Headline metric: **anchor rate** —
what fraction of cited quotes resolved to an offset region.

```sh
# Smoke (3 questions, balanced across buckets):
uv run python -m evals.run --reasoning low --limit 3

# Full golden set:
uv run python -m evals.run --reasoning medium

# Merge deterministic results with a manually produced judge JSONL:
uv run python -m evals.judge.aggregate \
  evals/results/<ts>_..._.csv \
  evals/results/<ts>_..._judge.jsonl \
  --out evals/results/<ts>_..._combined.md
```

The runner is opt-in and burns real OpenAI tokens. Each run writes CSV,
JSON, Markdown, and `_traces.jsonl` artifacts under `evals/results/`.
`pytest -m eval` runs the eval test layer; default `pytest` skips it.

The LLM-as-judge layer is real but manual. There is intentionally no
code path, subprocess, or `--with-judge` flag that calls a judge model.
The judge prompt lives at [`evals/judge/prompt.md`](evals/judge/prompt.md);
run it from a code assistant against the deterministic `_traces.jsonl`,
write a `JudgeResult` JSONL validated by
[`evals/judge/schema.py`](evals/judge/schema.py), then use the aggregate
command above to merge deterministic + judge results.

See [`evals/README.md`](evals/README.md) for the metric definitions,
golden set structure, and judge workflow.

## Operational endpoints

| Endpoint | Auth | Purpose |
|---|---|---|
| `POST /api/admin/ingest` | `X-Admin-Token` | Parse `convictions/` into SQLite |
| `POST /api/chat` | `X-Chat-Token` | Run one agent turn |
| `GET  /api/config` | `X-Chat-Token` | Return the server-selected chat model |
| `GET  /api/chat/conversations` | `X-Chat-Token` | List stored conversations for the sidebar |
| `GET  /api/chat/conversations/{conversation_id}` | `X-Chat-Token` | Load one stored conversation |
| `GET  /api/chat/conversations/{conversation_id}/questions/{question_id}/steps` | `X-Chat-Token` | Load persisted debug steps for one historical question |
| `GET  /api/health` | — | Liveness check |

## Where things live

```
app/
  api/             # FastAPI routers — thin controllers, no business logic
  services/        # business logic; raises domain exceptions (never HTTPException)
  repositories/    # ALL SQLAlchemy queries; module-level async functions
  models/          # SQLAlchemy ORM
  schemas/         # Pydantic request/response shapes
  providers/       # LLMProvider, OpenAI adapter, StubLLM; only place that imports openai
  retrieval/       # Retriever protocol + BM25 adapter; lifecycle owned by app lifespan
  agent/           # Bounded loop, rewrite stage, structured-output schemas
    tools/         # The four read-only tools the agent can call
    resolver/      # Deterministic substring → (start, end) offset resolver
    prompts/       # System + rewrite prompts (markdown)
  config/          # Settings + DB engine plumbing — only place that calls os.getenv
alembic/           # Schema-of-record migrations
convictions/       # The 30-doc corpus
docs/              # architecture notes
evals/             # golden set + runner + metrics + comparator
frontend/          # Vite + React + Tailwind chat UI + architecture explainer
tests/             # Mirrors app/ + an `eval/` layer (skipped by default)
```
