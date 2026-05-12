
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
| Same-language responses | System-prompt instruction; no architecture impact. |
| PDF / Excel uploads (bonus) | **Not implemented in this submission.** Design exists (uploaded files become user-scoped passages and reuse the same retrieval / resolver pipeline); see "Not implemented in this version" below. |

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

### Why this works

1. **Matches the interviewer's stated philosophy.** "Models nowadays tend to work pretty well, so using tools is usually enough." Tool use is the literal interpretation; the offset resolver turns "usually enough" into "every citation links to a specific source region" for grounding.
2. **Mirrors Claude Code's design (with one deliberate asymmetry).** Claude Code is a constrained tool-using agent over a filesystem (`Glob`, `Grep`, `Read`, ...); this is a constrained tool-using agent over a passage store. Same pattern, different domain. The asymmetry: Claude Code runs grep-in-the-loop with no precomputed index (its corpus is source code, where exact-token search is decisive); we keep a sparse BM25 index because the corpus is natural-language PT/EN prose where grep alone misses paraphrase. See CLAUDE.md § "A note on the Claude Code analogy" for the full reasoning.
3. **Strongest provenance guarantee available.** Provider Citations APIs guarantee the cited text appears in the source. The resolver guarantees that *plus* every claim's quote was anchored to a specific `(start, end)` region of a passage we cited — and works on every provider.
4. **Scales with the corpus.** No pre-built monolithic index to invalidate. `search_convictions` can be upgraded from BM25 to hybrid to reranked over time with no architectural change.
5. **PDF/Excel uploads have a straightforward extension path.** Uploads are *not implemented in this version* (see "Not implemented in this version" below), but the design is straightforward: a `search_uploaded_files` and `read_uploaded_passage` pair would mirror the conviction tools, with uploads server-parsed into the same passage shape and scoped to a single conversation.
6. **Compound questions are first-class.** Multi-step search → multi-passage citation is the natural mode of operation, not a special case.

---

## Other architectures considered

### Classic hybrid retrieval pipeline (BM25 + dense embeddings + reranker)

**Sketch.** Index passages once with BM25 + dense embeddings (`bge-m3` for PT+EN). At query time: hybrid retrieve → rerank with a cross-encoder → send top-K to the LLM with the citation contract. Optionally prepend per-chunk context summaries (Anthropic-style Contextual Retrieval) before indexing.

**Why not chosen.**
- The interviewer's signal — *"using tools is usually enough"* — points away from this much machinery.
- Six pieces (chunker, BM25, embedder, vector index, fusion, reranker) to build, defend in interview, and maintain.
- **Single-shot retrieval is the failure mode**: if the right passage isn't in top-K on the first attempt, the answer is wrong regardless of LLM quality. The agent loop in the chosen architecture mitigates this by allowing the model to re-query.
- Pre-built index drifts as the corpus is edited — same problem Anthropic cited when removing RAG from Claude Code.
- Multilingual embedding selection adds risk on a corpus with both PT and EN.

**Where it lives in the chosen design.** This pipeline is the *implementation* of the `search_convictions` tool, not the architecture. **v1 ships BM25-only over SQLite** with unicode-fold + accent-strip + lowercase normalization. The choice is justified by two assumptions that hold today and are likely to break later — agent loop, tool surface, citation contract, and resolver are unchanged at every step:

- **Small corpus (~30 docs).** BM25 stays useful as the corpus grows (best for exact-term matches: tickers, regulation numbers, acronyms like `FGC`, `CVM`, `IR`), but new failure modes appear. *Hundreds of docs:* near-duplicates and topical neighbors crowd the top-K — add a **cross-encoder reranker** (`bge-reranker-v2-m3` or Cohere `rerank-multilingual-v3`) over the top candidates. *Thousands of docs:* chunks pulled out of context lose meaning ("revenue grew 3%" — for which company?) — add **Anthropic-style Contextual Retrieval** (prepend a 50–100 token generated context summary to each chunk before indexing). *Tens of thousands+:* move lexical to OpenSearch / ParadeDB and dense to a dedicated vector store (Qdrant) or HNSW Postgres, plus metadata filtering and tenant sharding.
- **Internal-analyst audience.** Decade analysts speak the corpus vocabulary (PT/EN, regulatory terms), so on-vocabulary keyword queries work well with BM25. External users break that — Spanish-speaking clients ask `"tributación de CDB"` against `"tributação de CDB"` (BM25 misses on `ó`↔`ã`); English-only users ask `"how is CDB taxed?"` (zero word overlap with the PT passage); juniors paraphrase instead of using regulatory terms. The fix is a second retrieval path: a **multilingual embedding model** (OpenAI `text-embedding-3-large`, Cohere `embed-multilingual-v3`, or local `bge-m3`) over the same `passages` table with vectors in `pgvector`, fused with BM25 via Reciprocal Rank Fusion (k=60). Documented level-up.

### Hierarchical "table of contents, then zoom"

**Sketch.** Two LLM calls. First, the model receives a compact `list_documents()` output (id, title, passage count) and the question; it picks 1–3 relevant documents. Second, those documents are loaded in full and the model answers with passage-level citations.

**Why not chosen.**
- Cross-document themes are poorly served — *"what do all convictions say about IR taxation?"* needs section-level discovery across many docs, which a ToC-only router cannot provide.
- Bad router decision = bad answer. The chosen agent loop can recover by issuing a different search; a fixed two-step pipeline cannot.
- Loses some compound-question quality; the model can't iterate.

**Where it lives in the chosen design.** Its two tools — `list_documents(k)` and `read_document_outline(document_id)` — are absorbed into the agent's tool surface. The agent uses them when the question is broad ("what convictions cover retirement?") and uses `search_convictions` when the question is specific. We keep the strengths without the architectural rigidity.

### Provider-native grounding as the architecture (Anthropic Citations / OpenAI File Search / Gemini Grounding)

**Sketch.** Upload the corpus into the provider's hosted retrieval/grounding service; let the provider handle search and citations.

**Why not chosen.**
- **Direct conflict with provider portability**, which is an explicit requirement. Each provider's grounding feature has a different shape, different guarantees, and different data model. Switching providers means re-uploading, re-indexing, and rewriting the grounding layer.
- Anthropic Citations is incompatible with strict JSON Structured Outputs, which forces awkward response handling.
- OpenAI File Search is a provider-specific hosted retrieval product, so it does not fit the portable core architecture.
- Most importantly: **the offset resolver gives a stronger provenance shape than any provider feature.** Provider citations prove "this text was in the source." The resolver proves "this claim was drawn from a passage we cited, at *these* character offsets" — and the UI shows the user that exact region.

**Where it lives in the chosen design.** Behind provider adapters, as per-provider optimizations. Anthropic's Citations API would be useful in a future Anthropic adapter, but the current runtime path does not depend on it.

### Long-context "stuff every conviction into the prompt"

**Sketch.** Concatenate all convictions into a single cached system block; rely on prompt caching to reduce repeated input tokens; ask the model to cite passage IDs.

**Why not chosen.**
- Decade explicitly flags growth — *"as the number of documents grows, maintaining strict adherence becomes increasingly difficult."* This architecture *cannot* grow past a single model's context window; it commits us to a specific model family's limits.
- "Lost in the middle": accuracy can drop 10–20 pp when the key passage sits mid-context.
- Per-call input token footprint is high without cache hits; cold-start penalty is severe.

**Where it lives in the chosen design.** Nowhere. This option does not survive the growth requirement.

### Free-form fully agentic system (no constrained tool surface, model can do anything)

**Sketch.** Give the model open-ended tools, code execution, web access; let it figure out how to answer any question.

**Why not chosen.**
- Faithfulness is unverifiable when the model can pull from any source.
- Power without constraint is the wrong default for a *strictly grounded* assistant — the requirement is to refuse or disclaim when convictions don't cover something, not to fall back to general capability.
- Adds operational risk (sandboxing, latency variance) without addressing the core problem.

---

## Not implemented in this version

The following are designed but **out of scope for this submission**:

- **PDF / Excel uploads.** The bonus item from the challenge brief. Design: server-side parsing (`pypdf` / `pdfplumber` for PDF, `openpyxl` → markdown tables for Excel), parsed content becomes user-scoped passages with stable IDs in a per-conversation namespace, exposed via `search_uploaded_files(query, k)` and `read_uploaded_passage(passage_id)` — same shape as the conviction tools, same retrieval and resolver pipeline. Uploaded passages are explicitly *user context* (lower trust than convictions) and tagged accordingly in the system prompt.
- **Hybrid retrieval (BM25 + multilingual embeddings + RRF).** v1 ships BM25-only; hybrid is a documented level-up, gated on a cross-language eval failure plus a conversation with the project owner.
- **Cross-encoder reranker** inside `search_convictions`. Further level-up beyond hybrid; gated on its own eval failure. See "Classic hybrid retrieval pipeline" above.
- **Postgres + pgvector.** v1 ships SQLite + a Python BM25 library; Postgres is a documented level-up, justified by concurrency or index-size pressure neither of which exists at 30 docs.
- **Anthropic Citations API** inside the Anthropic adapter (per-provider optimization for free `cited_text` and deterministic indices). Adapter slot exists; the optimization is not wired in.

## Tier breakdown — production-grade vs deliberately simplified

This project ships two tiers of code; reviewers should be able to tell at a glance which one any file belongs to.

**Production-grade — built right:**

- Provider abstraction (`LLMProvider`, single-LLM-point rule)
- Offset resolver — deterministic substring → `(start, end)` mapping; the literal quote is dropped before the response is built
- Agent loop bounds (max 5 tool calls; `≥ 1` search before answer; tools dropped on forced-final turn)
- Audit log + raw token usage in every LLM step and response summary
- Response contract (deterministic disclaimer, language mirroring, schema-validated)
- Tool surface (read-only, hand-written JSON schemas, pure-function tests)
- Layering rules (Router → Service → Repository; CI-greppable — see `CLAUDE.md`)

**Deliberately simplified — well-known production paths exist; documented as level-up, not built:**

- SQLite + BM25-only retrieval (vs Postgres + pgvector + FTS; the hybrid path is documented as a level-up above)
- In-process FastAPI (vs Docker / k8s / multi-replica)
- Two-token auth only (chat + admin); no JWT/OAuth, no per-user identity, no rate limit
- File-based settings (vs secrets manager)
- 34 hand-written eval questions, deterministic metrics only (vs auto-generated bank + LLM-judge dashboard)
- No streaming (single sync `POST /api/chat`; SSE is out of scope)
- Single LLM provider (OpenAI; Anthropic adapter slot documented, not built)

Each level-up is described in the step where it would land. Promotion from "simplified" to "production-grade" is a conversation, not auto-triggered by the implementer. The frontend `Tiers` page renders this same matrix for live demos.

## Implementation order (eval-driven)

1. **Passage parser + store.** Markdown → passages with stable IDs.
2. **Provider abstraction.** `LLMProvider` protocol. **OpenAI adapter first** for LLM calls (`gpt-5.5` by default); embeddings are not implemented because v1 retrieval is BM25-only.
3. **`list_documents` + `read_passage` + `read_document_outline`** tools wired up.
4. **`search_convictions` — BM25-only over SQLite** with unicode-fold + accent-strip + lowercase normalization. Hybrid (BM25 + multilingual embeddings + RRF) is a documented level-up, gated on cross-language eval failure plus a conversation. See "Classic hybrid retrieval pipeline" in "Other architectures considered" for the full scaling story (corpus growth and audience expansion).
5. **Citation offset resolver.** Pure substring → `(start, end)` mapping; non-anchoring citations survive without a highlight. **Built before the agent loop** so every later step measures anchor rate from day one.
6. **Agent loop** with the system prompt enforcing all citation rules (Rule A, Rule B, clarifying-question, language mirroring). Multi-turn rewrite (`app/agent/rewrite.py`) is part of this step — prior assistant answers are never injected into the source-of-truth context.
7. **Disclaimer + audit log + token usage** wired into the orchestrator. SQLite is the storage; token usage is visible per LLM step and summarized per question.
8. **Eval suite.** Per-bucket floor: ≥ 3 questions, with Rule A and Rule B getting ≥ 4 each.
9. **Anthropic adapter (documented level-up, not built in v1)** — the protocol shape in `app/providers/base.py` proves portability today. A live second provider is a follow-up, and Citations API support would slot in there as a per-adapter optimization.
10. **Optional promotion to hybrid retrieval** if eval shows BM25 misses cross-cutting / cross-language questions. Beyond hybrid: cross-encoder reranker, then Anthropic-style Contextual Retrieval. Each promotion is a conversation, not auto-triggered.
11. **Bonus (out of scope for v1): upload pipeline** — parser-interface design lives in `app/services/parser/`.

Each step should pass the eval before moving to the next. Promotion beyond step 4 (reranker, Contextual Retrieval, real vector store) is gated on documented eval failures, not speculation.
