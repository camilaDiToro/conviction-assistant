
# Architecture — Decade AI Challenge

> **Constrained Agentic RAG with Deterministic Citation Verification.**
>
> A read-only tool-using agent over the conviction corpus, wrapped in a substring-verification layer that turns "the model usually grounds its answers" into "every shipped claim is provably grounded."

This is not a free-form agent. It is **constrained**: the model's only powers over the corpus are read-only tools, and every claim it produces must pass a deterministic check against the source before it reaches the user.

---

## Corpus snapshot

- 30 markdown documents in the starter package, ~8,664 lines, mixed Portuguese and English.
- Markdown is well-structured: `##` headings give natural passage boundaries.
- **The corpus is expected to grow substantially.** Decade explicitly frames the problem as "as the number of documents grows, maintaining strict adherence becomes increasingly difficult." The architecture must scale past any single model's context window.

## Constraints

| Requirement | Architectural impact |
|---|---|
| Strict grounding on convictions | Every cited claim must resolve to a `(start, end)` region of the cited source passage; the popup shows the user exactly what was cited. Refuse or disclaim when out of scope. |
| Provider portability | No hard dependency on Anthropic-only or OpenAI-only features. Native APIs sit behind a provider interface. |

Provider-native grounding features (Anthropic Citations, OpenAI File Search, Gemini Grounding) might be useful but are not being considered as architecture, because they would break portability.

---

## The chosen architecture

### System flow

```
POST /api/chat
   │
   ▼
Conversation Orchestrator
   │
   ▼
Agent LLM with read-only tools
   ├── list_documents()
   ├── read_document_outline(document_id)
   ├── search_convictions(query, k)
   └── read_passage(passage_ids)
   │
   ▼
Evidence Pack          (passages the agent decided to use)
   │
   ▼
Answer Generator       (produces JSON: answer + citations)
   │
   ▼
Citation Verifier      (deterministic substring match per quote)
   │
   ▼
Anchored citation  ─or─  citation surfaces without a highlight
   │
   ▼
Response
```

### What a passage is

A **passage** is the smallest citable unit of the conviction corpus. Convictions are markdown, so passages are sections delimited by `##` headings.

```json
{
  "id": "fixed_income#lci",
  "document_id": "fixed_income",
  "document_title": "Fixed Income",
  "heading": "LCI",
  "heading_path": ["Fixed Income", "LCI"],
  "text": "..."
}
```

Passages are what the system **searches over, reads, cites, and verifies against.** The assistant never cites "the whole document" — it cites specific passages and exact quotes within them.

### Response contract

The structured response is one of two shapes — a regular **answer** (with citations) or a **clarifying question** (when the user's query is genuinely ambiguous). The `kind` field discriminates.

**Internal generator schema** (what the LLM produces, identical across providers):

```json
// kind = "answer"
{
  "kind": "answer",
  "answer": "...",
  "citations": [
    { "passage_id": "fixed_income#lci", "quote": "..." }
  ],
  "general_knowledge_used": false,
  "general_knowledge_section": null,
  "conflict_detected": false,
  "conflict_statement": null,
  "out_of_scope": false
}

// kind = "clarifying_question"
{
  "kind": "clarifying_question",
  "question": "Did you mean LCI or LCA?",
  "options": ["LCI", "LCA"]
}
```

`general_knowledge_used` / `general_knowledge_section` carry Rule A from `CLAUDE.md`: when the convictions don't cover a topic, general knowledge is allowed but **must be marked very, very clearly** in a separate field, never interleaved with cited claims.

`conflict_detected` / `conflict_statement` carry Rule B: when two cited convictions contradict each other, the model sets `conflict_detected: true` and writes the disagreement explicitly in `conflict_statement` so the analyst sees the tension instead of a silent pick.

**HTTP response wrapper** — adds friendly display fields, the deterministic disclaimer, and the per-step debug + token-usage payload:

```json
{
  "kind": "answer",
  "answer": "...",
  "general_knowledge_section": null,
  "citations": [
    {
      "passage_id": "cdbs_quick_guide#tributacao",
      "document": "cdbs_quick_guide.md",
      "heading": "Tributação: Tabela Regressiva",
      "passage_text": "...",
      "start": 16,
      "end": 33
    }
  ],
  "out_of_scope": false,
  "disclaimer": "This response is informational and does not constitute investment advice.",
  "usage_summary": {
    "llm_call_count": 2,
    "prompt_tokens": 1234,
    "completion_tokens": 56,
    "cached_tokens": 0,
    "reasoning_tokens": 0,
    "step_count": 4,
    "duration_ms": 8200
  },
  "debug": {
    "tool_calls": [
      { "step_id": "...", "kind": "tool_call", "name": "search_convictions", "detail": "returned 5 passages", "result": { "returned_passage_ids": ["..."] } }
    ],
    "steps": [
      { "step_id": "...", "kind": "llm_call", "name": "agent_loop", "usage": { "model": "...", "prompt_tokens": 1234, "completion_tokens": 56, "cached_tokens": 0, "reasoning_tokens": 0 } }
    ]
  }
}
```

The `disclaimer` is appended deterministically by the orchestrator (not the model) so it cannot be paraphrased or omitted. It lives in its own field so the resolver never tries to anchor it against a passage. The orchestrator picks the language to mirror the response language (PT / EN / ES).

### Tool surface

```python
list_documents(k: int) -> list[DocSummary]
# id, title, passage_count. The corpus-level table of contents.

read_document_outline(document_id: str) -> DocumentOutline
# document_id, document_title, passage_count, and an ordered list of
# headings with passage_id + heading + ordinal.

search_convictions(query: str, k: int = 5) -> list[PassageHit]
# v1: BM25-only over SQLite-indexed passages with unicode-fold +
# accent-strip + lowercase normalization. The corpus is 30 docs
# and BM25 may be sufficient; the contract supports hybrid as a
# deferred level-up gated on cross-language eval failure plus a
# conversation with the project owner.
# Returns passage_id, score, document_id, document_title, heading_path, snippet.

read_passage(passage_ids: list[str]) -> list[Passage]
# Full text of one or more passages by ID, returned in input order.
# The agent is expected to batch every passage it intends to cite into a
# single call rather than issuing one read_passage per id.
```

All four tools are defined once with JSON schemas and reused across every provider adapter — tool use is the most provider-portable surface area in modern LLM APIs.

### Tools layer (rules a reviewer should be able to grep for)

The four tools live under `app/agent/tools/`. The rules below are non-negotiable; they survive every later step.

1. **Tools are storage-agnostic.** Tool modules import only from `app/repositories/*`, `app/schemas/*`, `app/retrieval/*` helpers/contracts, `app/errors.py`, and `app/agent/tools/context.py`. They never import SQLAlchemy, `aiosqlite`, or any DB driver directly. Swapping the storage backend (e.g. SQLite → Postgres + pgvector) changes only `app/repositories/` and migrations.
2. **Dependency injection via `ToolContext`.** Every tool's first parameter is a `ToolContext` dataclass (`app/agent/tools/context.py`). It carries `session: AsyncSession` plus the retriever. The agent loop's call shape `execute_tool(name, args, ctx)` is stable — adding a new dependency never changes tool signatures.
3. **`ToolContext` is the DI seam, not a SQLite holder.** If a future repo backend exposes something other than an `AsyncSession`, `ToolContext` carries that instead. The tools see only what they need.
4. **Tool input schemas are hand-written JSON-schema dicts** in `app/agent/tools/registry.py`. Each schema satisfies OpenAI strict mode out of the box: `type: object`, every property listed in `required`, `additionalProperties: false`, no `default` values. The agent's *output* schema may be Pydantic-derived — that's a separate decision and does not retroactively pull tool inputs into Pydantic.
5. **Single tool registry.** `app/agent/tools/__init__.py` exports `TOOLS: dict[str, ToolEntry]` where `ToolEntry = (definition: ToolDefinition, func: Callable)`. The agent loop reads `TOOLS` once to advertise definitions to the LLM and to dispatch tool calls by name. `TOOLS[name].definition.name == name` is enforced by test.
6. **Tools raise typed `DomainError` subclasses on bad inputs** (`PassageNotFoundError`, `DocumentNotFoundError`). The agent loop catches these and feeds the error back to the LLM as a tool-error message; it never returns `None` from a tool that promised a value.

### Loop bounds (operational discipline)

The agent loop is bounded to keep behavior predictable and debuggable:

- **Low reasoning effort by default** for the rewrite and answer-generation calls (`agent_reasoning_effort = "low"`), configurable through settings.
- **Max 5 tool calls per turn.** Most questions resolve in 1–3.
- **At least one search must run before the model is allowed to emit a final answer.** Enforced by the orchestrator, not just the prompt.
- **No claims without citations.** Enforced by schema.
- **Every cited quote either anchors to passage offsets or surfaces without a highlight.** Enforced by the resolver — the literal quote is never stored or returned.

This gives the "modern models are smart" benefit without letting the model roam.

### The agent loop (gather → act → resolve)

1. **Gather context.** The model issues tool calls — typically a `list_documents` or `search_convictions`, then one or more `read_passage`s — under a system prompt that pins down the canonical rules:
   - **Cite or refuse.** Every claim must cite `passage_id` + verbatim `quote`. No claim ships without a citation, and quotes that aren't a substring of the cited passage lose their highlight in the popup.
   - **Always prefer a real conviction.** If any conviction mentions the topic, even tangentially, cite that conviction rather than fall back to general knowledge.
   - **General knowledge is allowed, but must be marked very, very clearly** in `general_knowledge_section`, never interleaved with cited claims. (Rule A; see `../CLAUDE.md`.)
   - **Surface conflicting convictions.** If two convictions contradict, cite both and state the disagreement explicitly. Never silently pick a side. (Rule B; see `../CLAUDE.md`.)
   - **Clarify only when truly ambiguous.** If the query can be reasonably interpreted, answer; only return `kind: "clarifying_question"` when answering would risk citing the wrong topic.
   - **Mirror the user's language** (PT / EN / ES).
2. **Take action.** Model emits the structured response (answer or clarifying-question).
3. **Resolve offsets.** The deterministic resolver runs on every `kind: "answer"` response (clarifying-question responses skip resolution — there are no citations to anchor). Each citation's quote becomes `(start, end)` offsets in the cited passage; the literal text is dropped before the response is built.

For compound questions like *"compare CDB and LCI from a tax perspective"*, the loop decomposes naturally:

```
1. search_convictions("CDB taxation")
2. search_convictions("LCI taxation")
3. read_passage on the strongest hit from each
4. answer with citations
5. resolver anchors each citation to (start, end) → return
```

### The offset resolver

For every citation in the model's response:

```
offsets = passage_text.find(citation.quote)
# (start, end) on success — citation anchors and the popup highlights the region
# None on failure   — citation still surfaces, popup shows passage without highlight
```

The literal `quote` is consumed here and never reaches storage or the wire response. Only `(passage_id, start, end)` survives. Non-anchoring citations are not stripped: the analyst still sees the cited passage, just without a visual anchor.

The resolver is **deterministic, provider-agnostic, and the architectural commitment of this project.** It gives a hard provenance guarantee — every claim links to a specific region of a specific passage — that no provider's native Citations API matches.

> **Framing:** the agent is responsible for *finding* evidence (it copies verbatim because LLMs copy substrings reliably); the resolver is responsible for *pinning* it to offsets (because LLMs cannot count characters reliably). Two responsibilities, two layers.

### Conversation memory

Multi-turn handling is deliberately conservative to avoid amplifying hallucinations across turns:

- **Recent conversation is used only to rewrite or contextualize the current question** (e.g., resolving "and what about LCAs?" against the prior turn).
- **Prior assistant answers are never injected into the source-of-truth context.** Each turn runs fresh tool calls against the conviction corpus.
- **Citations are fresh per turn.** A claim's offsets are resolved against the current turn's passages — there is no carry-over of citation provenance across turns.

This prevents the common failure mode where an earlier hallucination becomes part of later turns' context and gets reinforced.

### Deterministic disclaimer

Every response carries a regulatory disclaimer (*"This response is informational and does not constitute investment advice."* and PT/ES equivalents). The orchestrator appends it deterministically — never the model — so it can never be paraphrased or omitted. It lives in a dedicated `disclaimer` field on the HTTP response, separate from `answer`, so the resolver never tries to anchor it against a passage.

### Audit log + token usage

Every step of every request is persisted. LLM calls carry raw token usage:

```
{
  step_id, question_id, conversation_id, timestamp,
  kind: "llm_call" | "tool_call" | "resolver" | "response",
  payload,        // request/response or tool args/result
  usage           // { model, prompt_tokens, completion_tokens, cached_tokens, reasoning_tokens } for llm_call
}
```

The log lives in **SQLite** (table `audit_log`) — same database that holds the passages and conversations. Postgres is a documented level-up if/when concurrency or full-text indexing outgrows SQLite. The HTTP `debug` payload exposes per-step usage; `usage_summary` carries per-question token totals. Adapters return token counts only.

### Provider abstraction

```python
class LLMProvider:
    def generate(messages, *, tools=None, schema=None, reasoning_effort=None, max_output_tokens=None) -> Response: ...
```

The current implementation ships the provider contract plus `OpenAILLM` for production and `StubLLM` for CI/tests. Anthropic and Gemini adapters are documented follow-ups, not present runtime code. Provider-native grounding features (Anthropic Citations, OpenAI File Search) would live **only inside their respective adapters as optimizations**, never as architecture. For example:

- A future Anthropic adapter could use the Citations API to get verbatim `cited_text`, deterministic char indices, and free output tokens.
- The OpenAI adapter falls back to JSON-schema prompt-based citations.
- The contract above the adapter is identical, so the orchestrator and resolver never know which provider is in use.

