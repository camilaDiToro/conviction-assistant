# ROADMAP — Multi-Session Build Plan

Step-by-step plan for building this project across multiple ~2–3 hour sessions. Each step has a hard scope cap. Update this file between sessions: check off completed steps with `- [x]` in the header and note any deviation.

For the *why* and the architectural commitments that govern every step, see `CLAUDE.md` § "Layering & single-LLM-point". For background research and rejected alternatives, see `docs/ARCHITECTURES.md`.

---

## Step 0 — Materialize roadmap + repo housekeeping  - [x]

- **Goal:** This file exists; CLAUDE.md indexes it; existing commits follow new convention; commit-style preference saved as memory.
- **Scope cap:** No code yet.
- **Files:** `docs/ROADMAP.md`, `CLAUDE.md` (additions only).
- **Acceptance:** `git log --oneline` shows two commits, each ≤ 150 chars, no Co-Authored-By trailer; `CLAUDE.md` references this file and contains the four layering rules.
- **Depends on:** none.

---

## Backend track (B1–B10)

### B1 — Project skeleton + config + health endpoint  - [x]
- **Goal:** runnable empty FastAPI app with the layered `app/` skeleton, Pydantic settings, ruff + pytest configured.
- **Scope cap:** no parser, no DB, no providers. Just plumbing. Resist writing classes "you'll need anyway."
- **Files:** `pyproject.toml`, `app/config.py`, `app/main.py`, `app/api/health.py`, `tests/test_health.py`, `.env.example`, `README.md` skeleton.
- **Acceptance:** `uv run uvicorn app.main:app --reload` starts; `GET /health` returns `{"status":"ok"}`; `pytest` runs (one test); `ruff check` clean.
- **Depends on:** none.

### B2 — Markdown parser + Passage model (in-memory; no DB yet)
- **Goal:** pure parser turning `convictions/*.md` into `list[Passage]` with stable IDs and `Updated` dates (where present).
- **Scope cap:** in-memory only. No Postgres. No embeddings. No tools yet.
- **Files:** `app/models.py` (Passage, DocSummary, Heading), `app/parser/markdown.py`, `app/parser/dates.py`, `app/parser/cli.py`, `tests/parser/test_markdown.py`, `tests/parser/test_dates.py`, `tests/parser/test_corpus_snapshot.py`.
- **Acceptance:**
  - Date extraction handles all 6 known variants: header italic/bold, EN/PT, `Atualizado`/`Atualização`/`Updated`/`Last Updated`/`Última Atualização`, with or without `de`, footer markers (e.g. ending in ` | Decade Investment Research`). When two markers exist, take the later one. When none, `updated=None` — never inferred.
  - Snapshot test pins: 30 documents → expected passage count; the ~13 documents whose `updated` is `None`; stable passage IDs (slug-based) for every passage.
  - `python -m app.parser.cli convictions/` prints: total passages, language breakdown, dated/undated counts, top-5 longest passages.
  - Slugification rule documented in `app/parser/markdown.py` docstring (NFKD-strip-accents, lowercase, dash-join, collapse-double-dashes).
  - Per-passage language detection (heuristic: accents + common stopwords). Tested against fixtures.
- **Depends on:** B1.

### B3 — Postgres store + ingestion command
- **Goal:** schema + repository layer; ingestion command writes parser output to DB.
- **Scope cap:** SQL FTS and pgvector columns are *defined* in the schema but the embedding column stays NULL (B6 fills it). No retrieval logic yet.
- **Files:** `docker-compose.yml` (Postgres 16 + pgvector), `migrations/001_init.sql` (passages + audit_log), `app/store/db.py`, `app/store/passages.py` (`get`, `list_documents`, `read_outline`, `upsert_many`), `app/ingest.py`, `tests/store/test_repo.py`.
- **Acceptance:** `docker compose up -d postgres && python -m app.ingest convictions/` populates DB; repo methods return expected shapes; integration test against the live DB.
- **Depends on:** B2.

### B4 — Provider abstractions + OpenAI adapter + StubProvider
- **Goal:** `LLMProvider` and `EmbeddingProvider` protocols, OpenAI adapter, **and** a `StubProvider` for tests. Cost tracking in the adapter.
- **Scope cap:** no agent loop. No tools. Just `provider.generate(...)` and `embedder.embed(...)` working in isolation, with usage + cost returned.
- **Files:** `app/providers/__init__.py` (factory keyed by `settings.LLM_PROVIDER`), `app/providers/base.py` (protocols + types), `app/providers/openai.py`, `app/providers/stub.py`, `app/providers/pricing.py`, `tests/providers/test_stub.py`, `tests/providers/test_pricing.py`. Manual smoke at `scripts/smoke_openai.py`. **No real OpenAI calls in CI.**
- **Acceptance:** `StubProvider` returns canned responses driven by a fixture file; smoke script runs with `OPENAI_API_KEY` set; usage + cost flow back through `LLMResponse`.
- **Depends on:** B1.

### B5 — Three simple tools: list_documents, read_document_outline, read_passage
- **Goal:** the read-only tools the agent will eventually call. Pure functions over the repository. JSON schemas for tool-call advertisement.
- **Scope cap:** **not** `search_convictions` (B6). No agent. Tools unit-tested directly.
- **Files:** `app/tools/__init__.py` (registry), `app/tools/list_documents.py`, `app/tools/read_document_outline.py`, `app/tools/read_passage.py`, `app/tools/schemas.py`, `tests/tools/test_simple_tools.py`.
- **Acceptance:** each tool callable as a plain Python function and returns the documented shape; schemas validated against the return types.
- **Depends on:** B3.

### B6 — search_convictions: hybrid BM25 + dense + RRF
- **Goal:** the heavy retrieval tool. Generate embeddings during ingestion (re-run B3's ingest with `--with-embeddings`); FTS over `unaccent`-normalized text; pgvector cosine; fuse via RRF.
- **Scope cap:** no reranker. RRF constant `k` lives in `config.RRF_K` (default 60). Cross-language test (PT query → EN doc) is required.
- **Files:** `app/store/search.py`, `app/tools/search_convictions.py`, `migrations/002_indexes.sql`, `tests/tools/test_search_convictions.py`.
- **Acceptance:** ranked `PassageHit` list; cross-language test passes; latency < 200ms p95 locally on the 30-doc corpus.
- **Depends on:** B3, B4.

### B7 — Agent orchestrator: bounded loop + system prompt + structured output
- **Goal:** the agent that gathers evidence and produces an answer. **First real end-to-end run** (or with `StubProvider` for CI).
- **Scope cap:** no verifier yet. No HTTP endpoint yet. Just `agent.run(user_message) -> AgentResult` callable from a CLI.
- **Files:** `app/agent/loop.py` (max 5 tool calls, temperature=0, no answer until ≥1 search), `app/agent/prompts/system.md` (git-tracked; Rules A & B; language mirroring; clarifying-question guidance), `app/agent/schemas.py`, `scripts/demo_agent.py`, `tests/agent/test_loop_with_stub.py`.
- **Rule B in the prompt must explicitly handle undated convictions**: `"If document_updated is missing for one or both conflicting passages, say so — e.g. 'A (Abril 2026) and B (undated) disagree on …' — never silently pick the dated one as 'newer'."` Direct consequence of B2's finding that ~13 of 30 docs are dateless.
- **Acceptance:** with `StubProvider`, `python scripts/demo_agent.py "What is a CDB?"` runs deterministically; loop bounds enforced (test that a 6th tool call is rejected); system prompt is a markdown file, not a Python string; a fixture-driven test exercises the dated-vs-undated conflict path.
- **Depends on:** B5, B6.

### B8 — Citation verifier + retry-once-with-feedback
- **Goal:** deterministic substring verification of every citation; retry path on failure.
- **Scope cap:** no LLM-as-judge. Just substring + a documented normalization policy (NFC unicode + collapsed whitespace, ignore leading/trailing).
- **Files:** `app/verifier/substring.py`, `app/verifier/normalize.py`, `app/agent/loop.py` (extended: on verifier fail, re-prompt once; on second fail, strip the unverified claim or refuse), `tests/verifier/test_substring.py`.
- **Acceptance:** golden fixtures cover matching quote → pass; paraphrase → fail + retry; second failure → claim stripped. Normalization policy documented in module docstring.
- **Depends on:** B7.

### B9 — POST /chat endpoint + audit log + response wrapping
- **Goal:** HTTP-callable chat. Wraps the agent's structured output with enriched citations (document title, heading path, Updated date), deterministic disclaimer, `usage_summary`, optional `debug` block. Persists every step to `audit_log`.
- **Scope cap:** no streaming, no SSE, no auth. Single sync endpoint. Conversation memory is request-side: client sends the prior turns; backend rewrites the current question.
- **Files:** `app/api/chat.py`, `app/api/schemas.py`, `app/store/audit.py`, `tests/api/test_chat.py` (uses StubProvider end-to-end).
- **Acceptance:** `curl -X POST /chat -d '{"message":"...","history":[]}'` returns the full response shape; audit_log row written; disclaimer appended by the orchestrator (never the model); `general_knowledge_used` and conflicting-conviction surfacing tested with fixtures.
- **Depends on:** B8.

### B10 — Eval suite + Anthropic adapter (portability proof)
- **Goal:** golden Q/A bank (~30 items, buckets per `docs/TESTING.md`); `pytest -m eval` reports verifier pass rate. Add Anthropic adapter and re-run the suite to prove portability.
- **Scope cap:** no human-rater UI, no LLM-as-judge dashboard. Verifier pass rate is the headline metric. Anthropic Citations API is **not** wired (interface slot only).
- **Files:** `evals/golden_set.yaml`, `evals/run_eval.py`, `tests/eval/test_eval_suite.py` (skipped without API key), `app/providers/anthropic.py`.
- **Acceptance:** `pytest -m eval` runs against OpenAI and Anthropic via `LLM_PROVIDER`; both report a verifier pass rate; the report is markdown that pastes into the README.
- **Depends on:** B9.

**Backend done after B10.** Bonus PDF/Excel uploads are explicitly designed-not-built per `docs/ARCHITECTURES.md`.

---

## Frontend track (F1–F4)

Can begin as soon as B9 lands a working `POST /chat`. F1 alone has no backend dependency.

### F1 — Vite + React + TS + Tailwind scaffold + lib/api.ts
- **Goal:** static-built frontend mounted under FastAPI. `lib/api.ts` is the **only** module that knows the backend exists.
- **Scope cap:** no chat UI yet. Just shell + `lib/api.ts` + a "ping" component that calls `/health`.
- **Files:** `frontend/package.json`, `frontend/vite.config.ts`, `frontend/tailwind.config.ts`, `frontend/src/main.tsx`, `frontend/src/app.tsx`, `frontend/src/lib/api.ts`, `frontend/src/lib/types.ts`, `app/main.py` (mount static at `/`).
- **Acceptance:** `npm run dev` proxies `/chat` to FastAPI; `npm run build` outputs to `frontend/dist/` and FastAPI serves it at `/`. ESLint rule blocks `fetch`/`axios` outside `lib/api.ts`.
- **Depends on:** B1.

### F2 — Chat UI: message list + composer + answer rendering
- **Goal:** working chat screen that hits `/chat` and renders the answer text + plain citation list.
- **Scope cap:** no citation drawer (F3), no debug drawer (F4), no markdown rendering of answers.
- **Files:** `frontend/src/features/chat/ChatScreen.tsx`, `MessageList.tsx`, `Composer.tsx`, `useChat.ts`.
- **Acceptance:** type a question → see the answer with citation list (passage_id + quote). Conversation history sent on each turn.
- **Depends on:** F1, B9.

### F3 — Citation drawer + Rule A / Rule B visual treatment
- **Goal:** clickable citation chips open a side panel with full passage text, document title, heading path, Updated date. General-knowledge sections get a clearly distinct visual block (Rule A). Conflicting-conviction surfacing has its own treatment (Rule B).
- **Scope cap:** no inline-text-highlighting of the quoted span. No PDF rendering.
- **Files:** `frontend/src/features/chat/CitationChip.tsx`, `CitationDrawer.tsx`, `GeneralKnowledgeBlock.tsx`, `ConflictNotice.tsx`.
- **Acceptance:** clicking a citation opens the drawer; general-knowledge text impossible to confuse with grounded text; a fixture turn with two conflicting passages renders the conflict notice cleanly.
- **Depends on:** F2.

### F4 — Debug drawer (tool calls, verifier, usage_summary)
- **Goal:** developer/reviewer view of what the agent did. Fed by the `debug` block in `ChatResponse`.
- **Scope cap:** no replay, no tracing graph. Chronological list of steps + top-line cost / step count.
- **Files:** `frontend/src/features/debug/DebugDrawer.tsx`, `DebugStep.tsx`, `useDebug.ts`.
- **Acceptance:** drawer shows tool calls in order, verifier pass/fail, total tokens, total cost. Toggleable.
- **Depends on:** F2.

**Frontend done after F4.**

---

## Per-step working contract

When a session starts with "do step Bx" or "do step Fx":

1. Re-read this file for that step.
2. Re-read `CLAUDE.md` § "Layering & single-LLM-point".
3. Confirm dependencies are green (run the previous step's tests).
4. **Stay inside the scope cap.** Adding files outside the listed `Files:` block requires asking the user.
5. End with the acceptance criterion run + a one-paragraph "what's done / what's next".
6. Update this file: check off the step (`- [x]`) and note any deviation.

---

## Out of scope (do not attempt)

- PDF / Excel uploads (challenge bonus; deferred).
- Cross-encoder reranker inside `search_convictions` (gated on B10 eval failure).
- Anthropic Citations API inside the Anthropic adapter (provider-internal optimization slot).
- Streaming `/chat`.
- Auth, rate limiting, multi-tenant isolation.
- LLM-as-judge dashboard.

If any of these become priorities, add them as new steps here.
