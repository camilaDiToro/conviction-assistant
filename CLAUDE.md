# CLAUDE.md — Decade AI Challenge

Index for future Claude sessions working on this project. Read this first; follow the pointers.

## What this project is

A conversational AI assistant strictly grounded on Decade's investment conviction documents. The challenge brief is in `AI_CHALLENGE.md`. The corpus is in `convictions/` (30 markdown files, mixed Portuguese/English, expected to grow).

**One-line framing for the interview:** *a constrained agentic harness over the conviction corpus — inspired by Claude Code's "tools, not embeddings-as-the-retriever" philosophy — with a deterministic substring verifier as the grounding guarantee that no provider's Citations API matches.*

The architecture is a **constrained tool-using agent + deterministic citation verifier**: the model gets read-only tools over a passage store and produces structured answers; every cited quote is substring-verified against the source before it reaches the user.

## Project framing

**This is an interview challenge, not a production system.** Nobody will maintain this after delivery. Optimize for **code quality, clarity, and defensibility under interview questions** — not for ops resilience, CI/CD pipelines, multi-region deploys, or hypothetical future maintainers. The README's "production-readiness" section is an *audit* of what would change for production; it documents thinking, not code. See `docs/ASSUMPTIONS.md` § "Operational" for the full framing.

## Where to read what

| File | Purpose |
|---|---|
| `AI_CHALLENGE.md` | The challenge brief from Decade. The requirements live here. |
| `docs/ROADMAP.md` | **Multi-session step-by-step build plan.** Read this at the start of every implementation session. Update between sessions (check off `- [x]`, note deviations). |
| `docs/ARCHITECTURES.md` | **The chosen architecture.** Tool surface, agent loop, verifier, what's *not* implemented in this version, alternatives that were considered and rejected, eval-driven implementation order. |
| `docs/INSIGHTS.md` | Research notes on provider-built RAG (Anthropic / OpenAI / Google) and how Claude Code works internally. Explains *why* the tool-based design is the right answer. Has links and videos. |
| `docs/TESTING.md` | Testing strategy. Layer-by-layer test plan, faithfulness eval suite, CI tiers. Confirms the architecture is testable by construction. |
| `docs/QUESTIONS.md` | Open questions to ask Decade that could change the design. |
| `docs/ASSUMPTIONS.md` | Confirmed assumptions from the project owner. Read before making decisions. |
| `docs/RETRIEVAL_SCALE.md` | Why each corpus size implies a different retrieval stack. |
| `docs/SCALING.md` | What changes in the architecture as concurrent-user count grows. |
| `docs/DEPLOYMENT.md` | Concrete deploy plan: tech stack, hosting choice, architecture diagram, key decisions, scale path. |

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
3. **Hybrid BM25 + multilingual embeddings is the v1 baseline.** Multilingual retrieval is required from day 1 — the corpus is PT/EN and queries are PT/EN/ES, so BM25 alone has a cross-language failure mode. Promotion to a *reranker* (or larger retrieval pipeline) is what's gated on eval failures. See `docs/RETRIEVAL_SCALE.md`.
4. **No prior assistant answers in the source-of-truth context.** Each turn runs fresh tool calls. Prior conversation is used only to rewrite the current question.
5. **The agent loop is bounded.** Max 5 tool calls, `temperature=0`, no final answer until at least one search has run. Enforced by the orchestrator, not the prompt.
6. **Tests run without an LLM by default.** LLM-in-the-loop is isolated to the eval pipeline. Unit + integration CI never burns provider tokens.
7. **Cost tracking is mandatory at three granularities** — per step, per question, per conversation. Every LLM call returns a `usage` block; the orchestrator stamps every step with IDs; the HTTP response includes per-step usage in `debug` and a `usage_summary` at the top. See `docs/ASSUMPTIONS.md` § "Cost tracking — REQUIRED" for the schema.

## In scope for v1

- Markdown ingestion → passage store with stable IDs (incl. `Updated:` date extraction)
- `LLMProvider` and `EmbeddingProvider` abstractions; **OpenAI adapter first** (`gpt-5` + `text-embedding-3-large`), Anthropic adapter second (portability proof)
- Four read-only tools: `list_documents`, `read_document_outline`, `search_convictions` (hybrid BM25 + multilingual embeddings, RRF), `read_passage`
- Bounded agent loop with structured-JSON output
- Deterministic citation verifier with retry-once-with-feedback
- Disclaimer + audit log + cost tracking on every response
- `POST /chat` endpoint
- Lightweight React frontend (Vite + React + TypeScript + Tailwind; built to static files and mounted under FastAPI)
- Eval suite (~30 hand-written Q/A) with verifier pass rate as headline metric

## Out of scope for v1 (designed, not built)

- PDF / Excel uploads (the challenge bonus)
- Cross-encoder reranker inside `search_convictions`
- Anthropic Citations API optimization inside the Anthropic adapter

See `docs/ARCHITECTURES.md` § "Not implemented in this version" for the design.

## Implementation order

Documented in `docs/ARCHITECTURES.md` § "Implementation order (eval-driven)". Each step should pass the eval before moving to the next.

## Design decisions explicitly considered and rejected

Documented so future sessions don't re-litigate them.

- **`confidence: high|medium|low` field on the response.** Adds an unverifiable signal — the model self-reports confidence, which is exactly the kind of thing we don't want to trust. The verifier pass/fail is a stronger and more honest signal. Rejected.
- **`/retrieve` endpoint alongside `/chat`** (returns retrieved evidence without generation). Genuinely useful for the demo; not required for v1. May be added if time allows.
- **`/eval` endpoint** for running the eval suite via HTTP. Replaced by the `pytest -m eval` suite documented in `docs/TESTING.md` — better dev ergonomics, no production endpoint to secure.
- **Lightweight evidence-selector model inside `search_convictions`.** A second small model that picks the best 4–8 of the fused top-30. Correct technique at thousands+ docs; premature for v1. The RRF fusion of BM25 + embeddings is *already* in v1 — that part is not rejected, it's the baseline. See `docs/RETRIEVAL_SCALE.md`.
- **Cross-encoder reranker** inside `search_convictions`. Adds a model + latency. Justified at hundreds+ docs; deferred until eval shows hybrid retrieval misses cross-cutting questions. See `docs/RETRIEVAL_SCALE.md`.

## Layering & single-LLM-point (hard rules)

These four rules are non-negotiable. They keep the codebase swappable, testable, and honest. Code review (and CI grep) enforces them.

### Backend layout

```
app/
  config.py        # env-var loading; the only place os.getenv lives
  models.py        # shared Pydantic models (Passage, Citation, ChatRequest, ...)
  parser/          # pure: markdown -> passages; no I/O beyond file reads
  store/           # repository pattern; Postgres access; no business logic
  providers/       # LLMProvider + EmbeddingProvider protocols + adapters
                   # *** SINGLE POINT OF LLM INTERACTION ***
  tools/           # agent tools as pure functions over the store
  agent/           # orchestrator, system prompt file, loop
  verifier/        # substring verifier
  api/             # FastAPI routes; thin — delegates to agent
  main.py
```

**Hard rules:**
1. **No code outside `app/providers/` ever imports `openai`, `anthropic`, or any provider SDK.** Including tests. CI greps for this.
2. **No code outside `app/store/` runs SQL.** Tools and the agent talk to the repository.
3. **No code outside `app/config.py` calls `os.getenv`.** All settings flow through `config.settings`.
4. **No business logic in `app/api/`.** Routes parse request → call agent → wrap response.

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
