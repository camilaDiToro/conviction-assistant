# ROADMAP — Multi-Session Build Plan

Step-by-step plan for building this project across multiple ~2–3 hour sessions. Each step has a hard scope cap. Update this file between sessions: check off completed steps with `- [x]` in the header and note any deviation.

For the *why* and the architectural commitments that govern every step, see `CLAUDE.md` § "Layering & single-LLM-point". For background research and rejected alternatives, see `docs/ARCHITECTURES.md`.

---

## Production-grade vs deliberately simplified

This project ships two tiers of code. The split is deliberate, and reviewers should be able to tell which tier any file belongs to at a glance.

**Production-grade — built right, will survive a deep-dive:**

- Provider abstraction (`LLMProvider` / `EmbeddingProvider`, single-LLM-point rule)
- Citation verifier (deterministic, exhaustively tested, retry-with-feedback)
- Agent loop bounds (max 5 tool calls, ≥ 1 search before answer, `temperature=0`)
- Audit log + cost tracking (3 granularities)
- Response contract (deterministic disclaimer, language mirroring, schema-validated)
- Tool surface (read-only, JSON-schema-defined, pure-function tests)
- Layering rules (CI-greppable; see `CLAUDE.md` § Layering)

**Deliberately simplified — well-known production paths exist; documented as level-up, not built:**

- SQLite + Python BM25 (vs Postgres + pgvector + FTS — see B3 / B6 level-up)
- In-process FastAPI (vs Docker / k8s / multi-replica — see `docs/DEPLOYMENT.md`)
- No auth, no rate limit, no SSE streaming (single sync `/chat` — see B9)
- File-based settings (vs secrets manager)
- ~30 hand-written eval questions (vs auto-generated bank + LLM-judge dashboard — see B10)

Each level-up is documented in the step where it would land, so a reviewer can see we knew what we were skipping and why. Promotion from "simplified" to "production-grade" is a conversation, not auto-triggered by the implementer.

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
- **Files:** `pyproject.toml`, `app/config.py`, `app/main.py`, `app/api/health.py`, `tests/test_health.py`, `.env.example`, `README.md` skeleton, `.gitignore`.
- **Acceptance:** `uv run uvicorn app.main:app --reload` starts; `GET /health` returns `{"status":"ok"}`; `pytest` runs (one test); `ruff check` clean.
- **Depends on:** none.

### B2 — Markdown parser + Passage model (in-memory; no DB yet)  - [x]
- **Goal:** pure parser turning `convictions/*.md` into `list[Passage]` with stable IDs and `Updated` dates (where present).
- **Scope cap:** in-memory only. No SQLite. No embeddings. No tools yet.
- **Files:** `app/models.py` (Passage, DocSummary, Heading), `app/parser/markdown.py`, `app/parser/dates.py`, `app/parser/cli.py`, `tests/parser/test_markdown.py`, `tests/parser/test_dates.py`, `tests/parser/test_corpus_snapshot.py`.
- **Acceptance:**
  - Date extraction handles all 6 known variants: header italic/bold, EN/PT, `Atualizado`/`Atualização`/`Updated`/`Last Updated`/`Última Atualização`, with or without `de`, footer markers (e.g. ending in ` | Decade Investment Research`). When two markers exist, take the later one. When none, `updated=None` — never inferred.
  - Snapshot test pins: 30 documents → expected passage count; the ~13 documents whose `updated` is `None`; stable passage IDs (slug-based) for every passage.
  - `python -m app.parser.cli convictions/` prints: total passages, language breakdown, dated/undated counts, top-5 longest passages.
  - Slugification rule documented in `app/parser/markdown.py` docstring (NFKD-strip-accents, lowercase, dash-join, collapse-double-dashes).
  - Per-passage language detection (heuristic: accents + common stopwords). Tested against fixtures.
- **Depends on:** B1.

### B3 — SQLite store + ingestion command  - [x]
- **Goal:** schema + repository layer; ingestion command writes parser output to SQLite. **Production-grade contract** (typed async repository, transactional writes, idempotent re-ingest); **simplified implementation** (file-backed SQLite, single-process).
- **Scope cap:** no embeddings, no FTS index yet (B6 adds the BM25 index). The repository contract is what survives if we ever swap to Postgres.
- **Files:** `app/repositories/{db,passages}.py`, `app/services/ingest.py`, `app/api/admin.py`, `app/models/passage.py` (ORM), `app/schemas/{passage,ingest}.py` (Pydantic), `app/errors.py`, `alembic/` (migration `0001_initial_schema.py`), `tests/repositories/test_repo.py`, `tests/services/test_ingest.py`, `tests/api/test_admin.py`.
- **Acceptance:** `POST /admin/ingest` ingests `settings.convictions_dir` and returns `IngestResponse` with documents, passages, orphans_deleted; alembic-driven migration is idempotent; integration tests run against tmp-path SQLite files via async fixtures; a heading rename across re-ingest is destructive (passage IDs are slug-based; renamed headings get new IDs and old citations become orphans — surfaced in `orphans_deleted`).
- **Depends on:** B2.
- **Deviations from the original step description (intentional):**
  - **Stack pivot:** raw `sqlite3` + sync repo → **SQLAlchemy 2.x async** + AsyncSession + `select()` + aiosqlite, to match project stack-conventions (Router→Service→Repository, async-first FastAPI). See CLAUDE.md § Architecture.
  - **Migrations:** Alembic (not "no migrations tool"). `alembic/versions/0001_initial_schema.py` owns the schema; `db.migrate()` applies it; FastAPI lifespan calls migrate on startup.
  - **Surface:** `python -m app.ingest` CLI replaced with `POST /admin/ingest`. The parser dev CLI at `app/services/parser/cli.py` remains for parser-output inspection.
  - **Folders:** `app/store/` → `app/repositories/`; `app/parser/` → `app/services/parser/`; `app/models.py` (Pydantic) → `app/schemas/passage.py`; new `app/models/passage.py` for the ORM.
- **Level-up path (deferred, gated on conversation):** Postgres + pgvector if/when we need (a) concurrent writes from multiple replicas, (b) full-text indexes that outgrow SQLite FTS5, (c) a vector search path that benefits from server-side ANN. The repository interface in `app/repositories/passages.py` is the swap point — no caller needs to change.

### B4 — Provider abstractions + OpenAI adapter + StubProvider
- **Goal:** `LLMProvider` and `EmbeddingProvider` protocols, OpenAI adapter, **and** a `StubProvider` for tests. Cost tracking in the adapter. Structured-output strategy lives here, in the adapter — OpenAI uses `response_format: json_schema (strict)`, the Anthropic adapter (B10) uses tool-call-as-output. Above the adapter, the contract is identical.
- **Scope cap:** no agent loop. No tools. Just `provider.generate(...)` and `embedder.embed(...)` working in isolation, with usage + cost returned. The OpenAI embedder ships even though B6 won't use it — keeps the adapter complete and unblocks the hybrid level-up if we ever take it.
- **Files:** `app/providers/__init__.py` (factory keyed by `settings.LLM_PROVIDER`), `app/providers/base.py` (protocols + types), `app/providers/openai.py`, `app/providers/stub.py`, `app/providers/pricing.py` (per-model price table; price changes are config, not code), `tests/providers/test_stub.py`, `tests/providers/test_pricing.py`. Manual smoke at `scripts/smoke_openai.py`. **No real OpenAI calls in CI.**
- **Acceptance:** `StubProvider` returns canned responses driven by a fixture file; smoke script runs with `OPENAI_API_KEY` set; usage + cost flow back through `LLMResponse`; structured output parses cleanly via the adapter.
- **Depends on:** B1.

### B5 — Three simple tools: list_documents, read_document_outline, read_passage
- **Goal:** the read-only tools the agent will eventually call. Pure functions over the repository. JSON schemas for tool-call advertisement.
- **Scope cap:** **not** `search_convictions` (B6). No agent. Tools unit-tested directly.
- **Files:** `app/tools/__init__.py` (registry), `app/tools/list_documents.py`, `app/tools/read_document_outline.py`, `app/tools/read_passage.py`, `app/tools/schemas.py`, `tests/tools/test_simple_tools.py`.
- **Acceptance:** each tool callable as a plain Python function and returns the documented shape; schemas validated against the return types.
- **Depends on:** B3.

### B6 — search_convictions: BM25-only retrieval
- **Goal:** working retrieval tool. **v1 ships BM25 only** because the corpus is 30 docs and BM25 may be sufficient; the contract supports hybrid as a deferred level-up. Tests are part of this step, not a follow-up.
- **Scope cap:** no embeddings, no fusion, no reranker. The point of v1 is to find out whether plain BM25 (with unicode-fold / accent-strip / lowercase normalization) clears the eval. If it does, embeddings are noise.
- **Files:** `app/store/search.py` (BM25 index built at startup over all passages; rebuilt on ingest; library: `bm25s`), `app/tools/search_convictions.py`, `tests/tools/test_search_convictions.py`, `tests/fixtures/retrieval_golden.yaml`.
- **Test-fixture authoring (part of this step, not optional):**
  1. Read every conviction in `convictions/` end-to-end.
  2. Hand-author **≥ 10** query → expected-`passage_id` pairs derived from the actual content. PT, EN, **and ES** queries each represented (ES queries against PT/EN passages — Spanish users do ask in Spanish).
  3. **≥ 1** cross-language case (PT query → EN passage, or vice versa).
  4. Mix of literal-match queries ("CDB tributação") and topic queries ("imposto de renda em renda fixa").
  5. Stored in `tests/fixtures/retrieval_golden.yaml`.
- **Acceptance:**
  - `search_convictions(query, k=5)` returns the expected `passage_id` in the top-`k` for **≥ 80%** of fixture cases (8/10).
  - Empty query → typed error, not 500.
  - Latency < 50 ms p95 locally on the 30-doc corpus.
  - **Cross-language case behavior:** if BM25 fails the cross-language fixture case, *do not auto-promote to hybrid*. Surface the failure in this step's writeup, and we decide together whether to add embeddings.
- **Depends on:** B3.
- **Level-up path (deferred, gated on conversation after eval):**
  1. **Hybrid BM25 + multilingual dense embeddings + RRF.** Embeddings: `text-embedding-3-large` (3072d) via the existing `EmbeddingProvider`, or `bge-m3` (1024d) if PT/EN cross-language proves weak. Vector storage: `sqlite-vec` extension or an in-memory numpy matrix at this corpus size (300 × N is trivial). Fusion: Reciprocal Rank Fusion, k=60.
  2. **Cross-encoder reranker** (a *further* step beyond hybrid, gated on its own eval failure).
  3. **Anthropic-style Contextual Retrieval** (per-chunk context summaries pre-pended at ingest) — gated on hundreds-of-docs scale.
  
  Promotion is a conversation, not auto-triggered. See `docs/RETRIEVAL_SCALE.md` for the longer reasoning per corpus size.

### B7 — Citation verifier + retry-once-with-feedback (built before the agent loop)
- **Goal:** deterministic substring verification of every citation; retry path on failure. **Built before the agent loop** so every later step can measure verifier pass rate from day one.
- **Scope cap:** no LLM-as-judge. Just substring + a *pinned* normalization policy.
- **Normalization policy (pinned in this step, not "decide later"):**
  - NFC unicode normalization on both quote and passage.
  - Strip soft-hyphens (U+00AD) and zero-width characters (U+200B–U+200D, U+FEFF).
  - Fold smart quotes to ASCII: `"` `"` `'` `'` → `"` `'`.
  - Normalize em-dash and en-dash to ASCII hyphen-minus.
  - Collapse runs of internal whitespace (incl. NBSP U+00A0) to a single space.
  - Diacritics **preserved** (PT/ES need them to round-trip).
  - Leading / trailing whitespace ignored.
- **Second-failure behavior (pinned):** strip the offending claim from the answer, never refuse the whole answer. If stripping leaves zero grounded claims, fall through to a safe refusal in the user's language (`kind: "answer"`, `out_of_scope: false`, `answer: <localized refusal>`).
- **Files:** `app/verifier/substring.py`, `app/verifier/normalize.py`, `tests/verifier/test_substring.py`, `tests/verifier/test_normalize.py`.
- **Acceptance:**
  - Golden fixtures cover: matching quote → pass; paraphrase → fail; cross-passage quote → fail (passage_id mismatch); empty quote → fail; smart-quote-mismatched quote → pass after normalization; NBSP-vs-space mismatch → pass; PT-with-diacritics → pass round-trip.
  - Property test: any random `passage.text[a:b]` slice (with `a < b` valid) verifies true against `passage.id`.
  - Normalization policy lives in `normalize.py` module docstring (the pinned list above), so changes go through code review.
- **Depends on:** B3.

### B8 — Agent orchestrator: bounded loop + system prompt + structured output
- **Goal:** the agent that gathers evidence and produces an answer. **First real end-to-end run** (or with `StubProvider` for CI). Built against the verifier from B7, so its first integration test *is* a verifier-pass-rate measurement.
- **Scope cap:** no HTTP endpoint yet. Just `agent.run(user_message, history) -> AgentResult` callable from a CLI.
- **Files:**
  - `app/agent/loop.py` — the loop itself (max 5 tool calls, `temperature=0`, ≥ 1 search before answer is allowed).
  - `app/agent/rewrite.py` — multi-turn question-rewrite. Uses prior turns to contextualize the current question; **never injects prior assistant answers as ground truth** (per the conversation-memory rule in `ARCHITECTURES.md` § Conversation memory).
  - `app/agent/prompts/system.md` — git-tracked markdown (not a Python string). Encodes Rules A & B, language mirroring, clarifying-question guidance, and the dated-vs-undated conflict guidance below.
  - `app/agent/schemas.py` — internal generator schema (`kind: "answer" | "clarifying_question"`, citations, `general_knowledge_used`, `general_knowledge_section`, `out_of_scope`).
  - `scripts/demo_agent.py` — CLI entry.
  - `tests/agent/test_loop_with_stub.py`.
- **Rule B in the prompt must explicitly handle undated convictions:** *"If `document_updated` is missing for one or both conflicting passages, say so — e.g. 'A (Abril 2026) and B (undated) disagree on …' — never silently pick the dated one as 'newer'."* Direct consequence of B2's finding that ~13 of 30 docs are dateless.
- **Acceptance:**
  - With `StubProvider`, `python scripts/demo_agent.py "What is a CDB?"` runs deterministically.
  - **Loop bound (upper):** test that a 6th tool call is rejected.
  - **Loop bound (lower):** test that a final answer emitted before any `search_convictions` call is rejected.
  - System prompt is a tracked markdown file, not a Python f-string.
  - Fixture-driven test exercises the dated-vs-undated conflict path.
  - Multi-turn rewrite test asserts that prior assistant text is **not** in the agent's tool-call context.
  - Verifier (from B7) runs on every test and pass rate is reported.
- **Depends on:** B5, B6, B7.

### B9 — POST /chat endpoint + audit log + response wrapping
- **Goal:** HTTP-callable chat. Wraps the agent's structured output with enriched citations (document title, heading path, `Updated` date), deterministic disclaimer, `usage_summary`, optional `debug` block. Persists every step to `audit_log` (SQLite); `cost_log` is a SQL view filtering to `kind = 'llm_call'` rows.
- **Scope cap:** no streaming, no SSE, no auth. Single sync endpoint.
- **ID ownership:** server generates `question_id` and `conversation_id` (UUIDv4) on every request. Client may send `conversation_id` to continue an existing conversation; server validates it's known and falls back to a new one on mismatch.
- **Language detection:** `app/agent/language.py` detects PT / EN / **ES** from the rewritten question (heuristic: stopwords + diacritics). Used for: response language mirroring (system prompt instruction), disclaimer language. ES users querying a PT/EN corpus is supported — answers are produced in ES, citations remain in source language.
- **Files:** `app/api/chat.py`, `app/api/schemas.py`, `app/store/audit.py` (writes), `app/agent/language.py`, `tests/api/test_chat.py` (uses `StubProvider` end-to-end).
- **Acceptance:** `curl -X POST /chat -d '{"message":"...","history":[]}'` returns the full HTTP response shape from `ARCHITECTURES.md` § "Response contract"; one `audit_log` row written per step; disclaimer appended by the orchestrator (never the model), in the detected language; `general_knowledge_used` and conflicting-conviction surfacing tested with fixtures; an ES question gets the ES disclaimer; `cost_log` view returns the right row count for an LLM-call sequence.
- **Depends on:** B8.

### B10 — Eval suite + Anthropic adapter (portability proof)
- **Goal:** golden Q/A bank (~30 items, buckets per `docs/TESTING.md`); `pytest -m eval` reports verifier pass rate. Add Anthropic adapter and re-run the suite to prove portability.
- **Scope cap:** no human-rater UI, no LLM-as-judge dashboard. Verifier pass rate is the headline metric. Anthropic Citations API is **not** wired (interface slot only).
- **Per-bucket floor:** ≥ 3 questions per bucket; **Rule A (tangential mention) and Rule B (conflicting convictions) get ≥ 4 each** since they're the highest-risk paths.
- **Files:** `evals/golden_set.yaml`, `evals/run_eval.py`, `tests/eval/test_eval_suite.py` (skipped without API key), `app/providers/anthropic.py`.
- **Acceptance:** `pytest -m eval` runs against OpenAI and Anthropic via `LLM_PROVIDER`; both report a verifier pass rate; the report is markdown that pastes into the README.
- **Depends on:** B9.

### B11 — README + production-grade-vs-simplified writeup
- **Goal:** the interview deliverable. README explains the architecture, embeds the eval results table from B10, lists the run instructions, and contains the production-readiness audit (which "deliberately simplified" parts have which level-up paths).
- **Scope cap:** no new code. This is a writing step.
- **Files:** `README.md` (full version replacing the B1 skeleton), maybe `docs/ARCHITECTURE_DIAGRAM.md` if a diagram earns its keep.
- **Acceptance:** README opens with the one-line framing from `CLAUDE.md`, embeds the eval table, lists `make run` / `make test` / `make eval` commands, and has a section "Production-grade vs deliberately simplified" reusing the framing from this roadmap's intro.
- **Depends on:** B10.

**Backend done after B11.** Bonus PDF/Excel uploads are explicitly designed-not-built per `docs/ARCHITECTURES.md`.

---

## Frontend track (F1–F4)

Can begin as soon as B9 lands a working `POST /chat`. F1 alone has no backend dependency.

### F1 — Vite + React + TS + Tailwind scaffold + lib/api.ts
- **Goal:** static-built frontend mounted under FastAPI. `lib/api.ts` is the **only** module that knows the backend exists.
- **Scope cap:** no chat UI yet. Just shell + `lib/api.ts` + a "ping" component that calls `/health`.
- **Files:** `frontend/package.json`, `frontend/vite.config.ts`, `frontend/tailwind.config.ts`, `frontend/src/main.tsx`, `frontend/src/app.tsx`, `frontend/src/lib/api.ts`, `frontend/src/lib/types.ts`, `app/main.py` (mount static at `/`).
- **Acceptance:** `npm run dev` proxies `/chat` to FastAPI on the configured port; `npm run build` outputs to `frontend/dist/` and FastAPI serves it at `/` (with the API namespaced under `/api/*` to avoid the static-mount-vs-route collision); ESLint rule blocks `fetch`/`axios` outside `lib/api.ts`.
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
5. **Tests are part of the step**, not a follow-up. The step is not done until the acceptance tests pass.
6. End with the acceptance criterion run + a one-paragraph "what's done / what's next".
7. Update this file: check off the step (`- [x]`) and note any deviation.

---

## Out of scope (do not attempt without a conversation)

- **PDF / Excel uploads.** Challenge bonus; designed in `docs/ARCHITECTURES.md`, not built.
- **Postgres + pgvector.** SQLite ships v1; Postgres is the documented level-up under B3.
- **Hybrid retrieval (BM25 + dense + RRF).** BM25 ships v1; hybrid is the documented level-up under B6, gated on conversation after eval.
- **Cross-encoder reranker** inside `search_convictions`. Further level-up beyond hybrid; gated on its own eval failure.
- **Anthropic Citations API** inside the Anthropic adapter. Provider-internal optimization slot; not wired in B10.
- **Streaming `/chat`** (SSE). Single sync endpoint in v1.
- **Auth, rate limiting, multi-tenant isolation.**
- **LLM-as-judge dashboard.** Verifier pass rate is the headline; complementary judge metrics may be added later.

If any of these become priorities, add them as new steps here.
