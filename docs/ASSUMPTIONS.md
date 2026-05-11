# Assumptions — Decade AI Challenge

Answers gathered from the project owner that pin down design decisions.

---

## Product & use case

**End user:** internal analyst.

*Architectural impact:* refusal-when-out-of-scope is acceptable behavior — no need for a softer client-facing fallback or human handoff path. The system prompt can use direct language ("the convictions do not cover this") without diplomatic softening.

**Answer shape:** adapts to the question — short for "what's X?", longer for "compare X and Y", structured (e.g., a comparison table) when the question is comparative.

*Architectural impact:* no fixed response template; the system prompt instructs the model to pick the right shape. Eval metrics need to allow varied output formats (golden-set rubric, not exact-match).

### Out-of-scope handling — IMPORTANT

The assistant **may use general knowledge** when the convictions don't cover a topic, but this **MUST BE MADE VERY, VERY CLEAR** to the user. There is no acceptable scenario where a general-knowledge claim is presented as if it came from the convictions.

**Order of preference (must follow this order):**

1. **Always prefer a real conviction.** If any conviction mentions the topic — even tangentially — cite that conviction. The citation must include the passage ID, the document title, the heading path, and the exact quote, so the analyst can see *where* the convictions mention it.
2. **If no conviction covers it, general knowledge is allowed**, but the response must:
   - Begin the general-knowledge portion with a hard, unambiguous marker (e.g., a dedicated section heading like **"Not from Decade convictions — general knowledge:"** or a clear visual prefix).
   - Never interleave general-knowledge claims with conviction-grounded claims in the same paragraph or sentence without a clear delimiter.
   - Set `out_of_scope: true` (or a new finer-grained flag — see below) on the structured response so the UI / downstream consumers can render the warning prominently.

*Architectural impact:*

- The response schema needs to express **mixed** answers (some claims grounded, some general-knowledge). Proposed addition:
  ```json
  {
    "answer": "...",
    "citations": [...],
    "general_knowledge_used": false,
    "general_knowledge_section": null,
    "out_of_scope": false
  }
  ```
  When `general_knowledge_used: true`, `general_knowledge_section` carries the verbatim text of the general-knowledge portion, separated from the cited portion of `answer`.
- The verifier still substring-checks every `citations` entry against its `passage_id`, but allows the `general_knowledge_section` to exist without any citation requirement.
- The system prompt must explicitly instruct: *"If you use general knowledge, mark it clearly as 'Not from Decade convictions'. Always prefer to cite a real conviction if one mentions the topic, even tangentially."*
- The eval suite needs a bucket that explicitly tests this: a question on a topic only mentioned tangentially must produce a citation to the tangential mention rather than fall back to general knowledge.

### Conflicting convictions — IMPORTANT

When two or more convictions contradict each other on a topic, the assistant **MUST surface the conflict** to the analyst. **MUST NOT silently pick one.**

Required behavior:

- Cite **both** (or all) conflicting passages.
- State explicitly that the convictions disagree.
- The analyst makes the call; the assistant does not pretend a consensus exists.

*Architectural impact:*

- The system prompt must explicitly instruct: *"If convictions disagree, surface the conflict and cite all sides. Never silently pick one."*
- The eval suite needs an explicit "conflicting convictions" bucket: golden-set questions that target topics where two convictions contradict, where the expected answer cites both sides.

**Tone:** not architecturally important. The system prompt describes the audience — *"an internal investment analyst at Decade, fluent in markets terminology, fluent in Portuguese and English"* — and lets the model pick the appropriate register. No fixed style template.

## Corpus

**Projected corpus size:** design for the **current scale (~30–50 docs)**. **But BM25-only is not sufficient** because the corpus is PT/EN and queries are PT/EN/ES (Spanish queries against PT documents fail with bag-of-words alone). The v1 retrieval stack is **hybrid BM25 + multilingual dense embeddings, fused with RRF** — see `RETRIEVAL_SCALE.md` for the embedding-model alternatives and the full tier-by-tier scaling story.

**Default embedding model for v1:** OpenAI `text-embedding-3-large` (multilingual). Alternatives (`bge-m3` local, Cohere `embed-multilingual-v3`) are documented in `RETRIEVAL_SCALE.md` and slot in behind the same `EmbeddingProvider` interface.

**Conviction update cadence:** assumed **rare** (published once, occasional edits). Index is **rebuilt on deploy / container start** — no watched-folder, no webhook, no live-update path.

*Explicit assumption:* if convictions change between deploys, the running instance won't see the change until the next restart. Acceptable for v1; production would add a webhook or scheduled re-index. Documented as a known limitation in the README's "production-readiness" section.

**Source formats:** only markdown is implemented for v1, but the parser sits behind a `DocumentParser` interface so PDF, Word, Excel, and other formats can be plugged in later without touching the rest of the pipeline.

*Architectural impact:*

```python
class DocumentParser(Protocol):
    def can_parse(self, path: Path) -> bool: ...
    def parse(self, path: Path) -> list[Passage]: ...

# v1 ships with:
class MarkdownParser(DocumentParser): ...

# future-ready slots (not implemented):
# class PdfParser(DocumentParser): ...     # pypdf / pdfplumber
# class DocxParser(DocumentParser): ...    # python-docx
# class ExcelParser(DocumentParser): ...   # openpyxl
```

The ingestion pipeline iterates over registered parsers and dispatches each file by extension. Stable passage IDs are derived from `(document_id, heading_slug)`, which is format-agnostic — IDs survive a future migration of the same content from markdown to another format as long as `document_id` is preserved.

**Versioning:** convictions are **not versioned**. Only the latest matters. No need for a `version` field on passages.

**Languages:** Portuguese, English, **and Spanish**. The system prompt instructs the assistant to mirror the user's language. Any future embedding choice must support all three languages — `bge-m3` (multilingual) is the right pick if dense retrieval is ever added; English-only or PT-only embedding models are ruled out.

## Question types & evaluation

**Question shape mix:** the test set should be assumed to be a **mix of all three** — single-doc factual ("what's the IR rate on CDB?"), compound comparative ("compare LCI and CRA tax-wise"), and open-ended thematic ("what's the conviction on Brazilian small caps?").

*Architectural impact:* this is the worst-case shape for the architecture and the one we already designed for. The bounded agent loop with `search_convictions` + `read_passage` handles all three:
- Single-doc → one search, one read, answer.
- Comparative → two searches, two reads, answer that names both sides.
- Thematic → potentially multiple searches; loop bound (max 5 tool calls) keeps it from drifting.

The eval suite must include at least one bucket per shape, and the bilingual split now needs to cover PT, EN, **and** Spanish (per the Spanish addition above) — though Spanish coverage in v1 can be lighter than PT/EN since the corpus is currently PT/EN-only.

**Grading strictness:** both **answer correctness** and **citation correctness** are important. An answer is only fully correct when both hold:

- The cited passage(s) actually exist and the quotes are verbatim substrings (deterministic check, the verifier).
- The cited passage is the *right* passage for the claim — not just any passage that contains a substring match.
- The answer text itself is factually correct given the cited evidence.

*Architectural impact:*
- The deterministic verifier covers (1) and is the headline metric.
- (2) is enforced by the eval suite via golden-set `expected_passage_ids` — the test fails if the model cites a different passage than the one we marked authoritative for the question.
- (3) is enforced by an LLM-as-judge entailment step (RAGAS / DeepEval `faithfulness`) that asks "is this claim entailed by the cited passage?"
- The README must report all three numbers separately so a reader can see where any failure lives.

## Performance, token usage, scale

### ⚠️ STRONG ASSUMPTION — Latency target ~5–10 seconds per response

This is a **load-bearing assumption** for the architecture. The bounded agent loop with multiple tool calls (search → read → answer → verify, plus possible retry) lands in the 3–8 second range on most providers. **5–10 s is achievable; anything tighter (<3 s) would force a single-shot retrieval design and break the agentic shape.**

If this assumption proves wrong, the architecture would need to change in non-trivial ways:
- Replace the agent loop with single-shot retrieval + answer (loses compound-question quality).
- Or aggressively pre-fetch and cache (loses freshness; harder verifier story).

This assumption is documented prominently because pivoting away from it later is expensive.

**Concurrent users (v1):** small internal team, **<10 concurrent users**. Single-instance FastAPI talking to one Postgres (Postgres FTS for BM25, pgvector for dense). No load balancer, no Redis, no real auth layer required for v1.

See `SCALING.md` for what changes if the user count grows to ~10–100 or 100+.

### Token usage — REQUIRED

Token usage is a first-class debugging and audit concern. Every LLM call must expose raw provider counters:

1. **Per step** — every LLM call records its own prompt tokens, completion tokens, cached tokens, and reasoning tokens.
2. **Per question** — the response summary aggregates those counters across the current turn.
3. **Audit replay** — persisted `llm_call` rows keep raw `usage` JSON so historical debug traces can be reconstructed.

*Architectural impact:*

- The `LLMProvider` interface returns a raw `usage` block on every call: `{model, prompt_tokens, completion_tokens, cached_tokens, reasoning_tokens}`.
- The orchestrator stamps every step with a `step_id`, `question_id`, and `conversation_id`.
- The `debug` payload in the HTTP response (already documented in `ARCHITECTURES.md` § "Citation contract") includes per-step usage; a `usage_summary` block at the top of the response carries per-question token totals.
- A persistent log (`audit_log`, the same table that records every step) carries raw `usage` so historical traces can be audited later.

This must work identically across providers: adapters expose token counts, and nothing above the adapter depends on provider-specific usage details.

**Streaming:** not required. Wait-for-full-answer is acceptable. The verifier runs cleanly post-hoc this way; no UX complications around mid-stream verification.

**Model choice:** **Primary provider for v1: OpenAI** (default model `gpt-5.5`); the Anthropic adapter is documented as the second adapter path to prove portability. Keep the chat route on the backend-selected default model; use evals, not per-request model controls, to justify changing it.

## Compliance, security, data

**PII / sensitive content:** none. Convictions are research material, not personal data. No need for zero-data-retention provider arrangements; provider-side prompt caching is allowed.

**Regulatory disclaimer:** every response must append a generic "not investment advice" line.

*Architectural impact:*
- The disclaimer is appended deterministically by the orchestrator (not the model) to guarantee it is never missing or paraphrased away by the LLM.
- Suggested text (PT/EN/ES, picked to match the response language): *"Esta resposta é informativa e não constitui recomendação de investimento."* / *"This response is informational and does not constitute investment advice."* / *"Esta respuesta es informativa y no constituye una recomendación de inversión."*
- The disclaimer is not part of the `answer` field that the verifier checks — it lives in a separate `disclaimer` field on the response, so it cannot accidentally be cited or substring-matched against a passage.

**Deployment:** keep it as simple as possible. No specific cloud / region / on-prem constraint for v1. Local dev or a single VM / managed container service (Render, Railway, Fly, ECS task — whatever is fastest) is acceptable.

**Provider restrictions:** none. Any provider can be used.

**Audit log:** every tool call and every citation must be persisted.

*Architectural impact:*
- An `audit_log` table records every step: `{step_id, question_id, conversation_id, timestamp, kind: "llm_call" | "tool_call" | "verifier" | "response", payload, usage}`. Same database that holds passages and conversations.
- Citations are persisted as part of the final response record so they can be replayed and re-verified later (e.g., if a conviction is edited and we want to know which past responses cited it).
- For v1, the log is local. Production would forward to a structured log destination and add retention policies (see `SCALING.md`).

## Conversation behavior

**Multi-turn:** yes. Conversation history matters within a session.

*Architectural impact:* the conversation-memory rule already documented in `ARCHITECTURES.md` § "Conversation memory" applies: prior assistant answers are **never re-injected** as source-of-truth context; recent turns are used only to **rewrite or contextualize** the current question (e.g., resolving "and what about LCAs?" against the previous turn). Each turn runs fresh tool calls and produces fresh citations.

**User profiles:** no. The assistant treats every user identically. No `user_context` field on the API.

**Clarifying questions:** the assistant **may** ask a clarifying question when a query is truly ambiguous instead of guessing.

*Architectural impact:*

- The structured response is one of two shapes — answer or clarifying-question:
  ```json
  // either:
  { "kind": "answer", "answer": "...", "citations": [...], "out_of_scope": false, ... }
  // or:
  { "kind": "clarifying_question", "question": "Did you mean LCI or LCA?", "options": ["LCI", "LCA"] }
  ```
- The system prompt instructs the model to prefer answering when the question can be reasonably interpreted; ask only when the ambiguity would lead to citing the wrong topic. Over-asking is bad UX.
- The orchestrator skips the verifier when `kind == "clarifying_question"` (no citations to check).
- The eval suite gets a small "ambiguity" bucket where the expected response is a clarifying question, not an answer.

**Cross-session memory:** no. Each conversation is independent. No persistent per-user memory.

## API surface & integration

**External integrations:** none. The assistant is standalone — no CRM, portfolio system, or ticketing integration. No "action" tools beyond the read-only conviction tools. Keeps the system bounded.

**Authentication:** simplest possible — a single API key (or no auth) for v1. No OAuth / JWT.

## Operational

### ⚠️ FRAMING — this is an interview challenge, not a production system

**No one maintains this after delivery.** This is a deliverable for a Decade interview, not a system that will run in production at Decade.

*What this means in practice:*
- Optimize for **code quality, clarity, and defensibility under interview questions**, not for ops resilience.
- The README's "production-readiness" section is an *audit* of what *would* change for production — it documents thinking, not actual production code.
- Don't add CI/CD pipelines, multi-region deploys, blue-green strategies, etc. They are noise in this context.
- Don't add abstractions for hypothetical future maintainers; the maintainer is the interviewer reading the code once.
- Do still write tests — they prove correctness and they will be read.
- Do still write the README well — it is the primary thing the interviewer reads.

This framing is mirrored in `../CLAUDE.md` § "Project framing".

**Observability infrastructure:** no existing infra. We add minimal in-house logging via the per-step audit log already documented in this file. No Langfuse / Arize integration in v1.

*Brief note for the project owner:* "observability" tooling here means platforms that capture LLM call traces, latency, token usage, and prompt/response pairs (Langfuse, Arize, LangSmith are common ones). They give you a dashboard view of every agent run. We don't need one for v1 — the audit log gives the same data, just without the dashboard.

**Dry-run mode:** **not implemented.** The `debug` payload already exposes the tool trace and verifier result on every real response, which gives the same debugging value with less code. If the project owner asks for dry-run during the demo, it is a one-day add: short-circuit before the answer-generation step and return the planned tool sequence.

**Production feedback loop (thumbs up/down):** not implemented for v1.

**Frontend:** **Vite + React + TypeScript + Tailwind** — the lightest *real React* setup. Single-page app, builds to plain static files (no SSR, no node runtime in production). Default deploy is to mount the Vite `dist/` under FastAPI at `/` — single service, single URL, no CORS. Optional alternative: deploy `dist/` separately to Vercel and point at the API by URL. See `DEPLOYMENT.md` for the full frontend section.
