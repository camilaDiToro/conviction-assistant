
# Architecture — Decade AI Challenge

> **Constrained Agentic RAG with Deterministic Citation Verification.**
>
> A read-only tool-using agent over the conviction corpus, wrapped in a substring-verification layer that turns "the model usually grounds its answers" into "every shipped claim is provably grounded."

This is not a free-form agent. It is **constrained**: the model's only powers over the corpus are read-only tools, and every claim it produces must pass a deterministic check against the source before it reaches the user.

---

## Corpus snapshot

- 30 markdown documents in the starter package, ~13,737 lines, mixed Portuguese and English.
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
POST /chat
   │
   ▼
Conversation Orchestrator
   │
   ▼
Agent LLM with read-only tools
   ├── list_documents()
   ├── read_document_outline(doc_id)
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
Retry once with feedback  ─or─  safe refusal  ─or─  pass through
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
  "heading_path": ["Fixed Income", "LCI"],
  "language": "en",
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
  "out_of_scope": false
}

// kind = "clarifying_question"
{
  "kind": "clarifying_question",
  "question": "Did you mean LCI or LCA?",
  "options": ["LCI", "LCA"]
}
```

`general_knowledge_used` / `general_knowledge_section` carry the rule from `ASSUMPTIONS.md` § "Out-of-scope handling — IMPORTANT": when the convictions don't cover a topic, general knowledge is allowed but **must be marked very, very clearly** in a separate field, never interleaved with cited claims.

**HTTP response wrapper** — adds friendly display fields, the deterministic disclaimer, and the per-step debug + cost payload:

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
    "question_total_cost_usd": 0.014,
    "conversation_total_cost_usd": 0.041,
    "step_count": 4
  },
  "debug": {
    "tool_calls": [
      { "tool": "search_convictions", "arguments": { "query": "...", "k": 8 }, "returned_passage_ids": ["..."] }
    ],
    "steps": [
      { "step_id": "...", "kind": "llm_call", "model": "...", "usage": { "prompt_tokens": 1234, "completion_tokens": 56, "cached_tokens": 0 }, "cost_usd": 0.003 }
    ]
  }
}
```

The `disclaimer` is appended deterministically by the orchestrator (not the model) so it cannot be paraphrased or omitted. It lives in its own field so the resolver never tries to anchor it against a passage. The orchestrator picks the language to mirror the response language (PT / EN / ES).

### Tool surface

```python
list_documents() -> list[DocSummary]
# id, title, one-line summary, language. The "table of contents."

read_document_outline(doc_id: str) -> list[Heading]
# Heading tree of one document so the model can pick the right
# section without reading the whole thing.

search_convictions(query: str, k: int = 8) -> list[PassageHit]
# v1: BM25-only over SQLite-indexed passages with unicode-fold +
# accent-strip + lowercase normalization. The corpus is 30 docs
# and BM25 may be sufficient; the contract supports hybrid as a
# deferred level-up gated on cross-language eval failure plus a
# conversation with the project owner. See ROADMAP B6.
# Returns id, doc_title, heading_path, snippet, score.

read_passage(passage_ids: list[str]) -> list[Passage]
# Full text of one or more passages by ID, returned in input order.
# The agent is expected to batch every passage it intends to cite into a
# single call rather than issuing one read_passage per id.
```

All four tools are defined once with JSON schemas and reused across every provider adapter — tool use is the most provider-portable surface area in modern LLM APIs.

### Tools layer (rules a reviewer should be able to grep for)

The four tools live under `app/tools/`. The rules below are non-negotiable; they survive every later step.

1. **Tools are storage-agnostic.** Tool modules import only from `app/repositories/*`, `app/schemas/*`, `app/errors.py`, and `app/tools/context.py`. They never import SQLAlchemy, `aiosqlite`, or any DB driver directly. Swapping the storage backend (e.g. SQLite → Postgres + pgvector under ROADMAP B3 level-up) changes only `app/repositories/` and migrations.
2. **Dependency injection via `ToolContext`.** Every tool's first parameter is a `ToolContext` dataclass (`app/tools/context.py`). At v1 it carries `session: AsyncSession`; B6 adds `bm25_index`. The agent loop's call shape `execute_tool(name, args, ctx)` is therefore stable from B5 onward — adding a new dependency never changes tool signatures.
3. **`ToolContext` is the DI seam, not a SQLite holder.** If a future repo backend exposes something other than an `AsyncSession`, `ToolContext` carries that instead. The tools see only what they need.
4. **Tool input schemas are hand-written JSON-schema dicts** in `app/tools/registry.py`. Each schema satisfies OpenAI strict mode out of the box: `type: object`, every property listed in `required`, `additionalProperties: false`, no `default` values. The agent's *output* schema in B8 may be Pydantic-derived — that's a separate decision and does not retroactively pull tool inputs into Pydantic.
5. **Single tool registry.** `app/tools/__init__.py` exports `TOOLS: dict[str, ToolEntry]` where `ToolEntry = (definition: ToolDefinition, func: Callable)`. The agent loop in B8 reads `TOOLS` once to advertise definitions to the LLM and to dispatch tool calls by name. `TOOLS[name].definition.name == name` is enforced by test.
6. **Tools raise typed `DomainError` subclasses on bad inputs** (`PassageNotFoundError`, `DocumentNotFoundError`). The agent loop catches these and feeds the error back to the LLM as a tool-error message; it never returns `None` from a tool that promised a value.

Per-tool decisions (return shapes, sort orders, descriptions) live in `docs/b5-decisions.md`.

### Loop bounds (operational discipline)

The agent loop is bounded to keep behavior predictable and debuggable:

- **`temperature = 0`** for the answer-generation step.
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

Every response carries a regulatory disclaimer (*"This response is informational and does not constitute investment advice."* and PT/ES equivalents). The orchestrator appends it deterministically — never the model — so it can never be paraphrased or omitted. It lives in a dedicated `disclaimer` field on the HTTP response, separate from `answer`, so the resolver never tries to anchor it against a passage. See `ASSUMPTIONS.md` § "Compliance, security, data" for the exact text per language.

### Audit log + cost tracking

Every step of every request is persisted. One log, two consumers (audit and cost):

```
{
  step_id, question_id, conversation_id, timestamp,
  kind: "llm_call" | "tool_call" | "resolver" | "response",
  payload,        // request/response or tool args/result
  usage           // { model, prompt_tokens, completion_tokens, cached_tokens } for llm_call
                  // (cost_usd is NOT stored — derived on render via app/services/cost.py)
}
```

The log lives in **SQLite** (table `audit_log`, with `cost_log` as a SQL view filtered to `llm_call` rows) — same database that holds the passages and conversations. Postgres is the documented level-up under `ROADMAP.md` § B3 if/when concurrency or full-text indexing outgrows SQLite. The HTTP `debug` payload exposes per-step usage; `usage_summary` carries per-question and per-conversation totals. **Adapters return token counts only; USD cost is derived in `app/services/cost.py` from a vendored pricing JSON** (`app/providers/_model_prices.json`, refreshed via `scripts/refresh_prices.py`) — price corrections re-price old audit-log rows retroactively, and the adapter never owns prices. See `docs/PRICING.md`.

See `ASSUMPTIONS.md` § "Cost tracking — REQUIRED" and § "Audit log".

### Provider abstraction

```python
class LLMProvider:
    def generate(messages, tools=None, schema=None) -> Response: ...
```

Adapters for Anthropic, OpenAI, Gemini. Provider-native grounding features (Anthropic Citations, OpenAI File Search) are used **only inside their respective adapters as optimizations**, never as architecture. For example:

- The Anthropic adapter can use the Citations API to get verbatim `cited_text`, deterministic char indices, and free output tokens.
- The OpenAI adapter falls back to JSON-schema prompt-based citations.
- The contract above the adapter is identical, so the orchestrator and resolver never know which provider is in use.

### Why this works

1. **Matches the interviewer's stated philosophy.** "Models nowadays tend to work pretty well, so using tools is usually enough." Tool use is the literal interpretation; the offset resolver turns "usually enough" into "every citation links to a specific source region" for grounding.
2. **Mirrors Claude Code's design (with one deliberate asymmetry).** Claude Code is a constrained tool-using agent over a filesystem (`Glob`, `Grep`, `Read`, ...); this is a constrained tool-using agent over a passage store. Same pattern, different domain. The asymmetry: Claude Code runs grep-in-the-loop with no precomputed index (its corpus is source code, where exact-token search is decisive); we keep a sparse BM25 index because the corpus is natural-language PT/EN prose where grep alone misses paraphrase. See CLAUDE.md § "A note on the Claude Code analogy" for the full reasoning.
3. **Strongest provenance guarantee available.** Provider Citations APIs guarantee the cited text appears in the source. The resolver guarantees that *plus* every claim's quote was anchored to a specific `(start, end)` region of a passage we cited — and works on every provider.
4. **Scales with the corpus.** No pre-built monolithic index to invalidate. `search_convictions` can be upgraded from BM25 to hybrid to reranked over time with no architectural change.
5. **PDF/Excel uploads have a low-cost extension path.** Uploads are *not implemented in this version* (see "Not implemented in this version" below), but the design is straightforward: a `search_uploaded_files` and `read_uploaded_passage` pair would mirror the conviction tools, with uploads server-parsed into the same passage shape and scoped to a single conversation.
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
- **Internal-analyst audience.** Decade analysts speak the corpus vocabulary (PT/EN, regulatory terms), so on-vocabulary keyword queries work well with BM25. External users break that — Spanish-speaking clients ask `"tributación de CDB"` against `"tributação de CDB"` (BM25 misses on `ó`↔`ã`); English-only users ask `"how is CDB taxed?"` (zero word overlap with the PT passage); juniors paraphrase instead of using regulatory terms. The fix is a second retrieval path: a **multilingual embedding model** (OpenAI `text-embedding-3-large`, Cohere `embed-multilingual-v3`, or local `bge-m3`) over the same `passages` table with vectors in `pgvector`, fused with BM25 via Reciprocal Rank Fusion (k=60). One-time embedding pass costs ~$0.02; per-query cost ~$0.0001. Documented level-up under `ROADMAP.md` § B6.

### Hierarchical "table of contents, then zoom"

**Sketch.** Two LLM calls. First, the model receives a compact `list_documents()` output (id, title, summary, language) and the question; it picks 1–3 relevant documents. Second, those documents are loaded in full and the model answers with passage-level citations.

**Why not chosen.**
- Cross-document themes are poorly served — *"what do all convictions say about IR taxation?"* needs section-level discovery across many docs, which a ToC-only router cannot provide.
- Bad router decision = bad answer. The chosen agent loop can recover by issuing a different search; a fixed two-step pipeline cannot.
- Loses some compound-question quality; the model can't iterate.

**Where it lives in the chosen design.** Its two tools — `list_documents()` and `read_document_outline(doc_id)` — are absorbed into the agent's tool surface. The agent uses them when the question is broad ("what convictions cover retirement?") and uses `search_convictions` when the question is specific. We keep the strengths without the architectural rigidity.

### Provider-native grounding as the architecture (Anthropic Citations / OpenAI File Search / Gemini Grounding)

**Sketch.** Upload the corpus into the provider's hosted retrieval/grounding service; let the provider handle search and citations.

**Why not chosen.**
- **Direct conflict with provider portability**, which is an explicit requirement. Each provider's grounding feature has a different shape, different guarantees, and different data model. Switching providers means re-uploading, re-indexing, and rewriting the grounding layer.
- Anthropic Citations is incompatible with strict JSON Structured Outputs, which forces awkward response handling.
- OpenAI File Search adds per-call charges ($2.50 / 1k calls) on top of token cost.
- Most importantly: **the offset resolver gives a stronger provenance shape than any provider feature.** Provider citations prove "this text was in the source." The resolver proves "this claim was drawn from a passage we cited, at *these* character offsets" — and the UI shows the user that exact region.

**Where it lives in the chosen design.** Behind provider adapters, as per-provider optimizations. Anthropic's Citations API is excellent and we use it inside the Anthropic adapter; we just don't *depend* on it.

### Long-context "stuff every conviction into the prompt"

**Sketch.** Concatenate all convictions into a single cached system block; rely on prompt caching to amortize cost; ask the model to cite passage IDs.

**Why not chosen.**
- Decade explicitly flags growth — *"as the number of documents grows, maintaining strict adherence becomes increasingly difficult."* This architecture *cannot* grow past a single model's context window; it commits us to a specific model family's limits.
- "Lost in the middle": accuracy can drop 10–20 pp when the key passage sits mid-context.
- Per-call input cost is high without cache hits; cold-start penalty is severe.

**Where it lives in the chosen design.** Nowhere. This option does not survive the growth requirement.

### Free-form fully agentic system (no constrained tool surface, model can do anything)

**Sketch.** Give the model open-ended tools, code execution, web access; let it figure out how to answer any question.

**Why not chosen.**
- Faithfulness is unverifiable when the model can pull from any source.
- Power without constraint is the wrong default for a *strictly grounded* assistant — the requirement is to refuse or disclaim when convictions don't cover something, not to fall back to general capability.
- Adds operational risk (sandboxing, cost, latency variance) without addressing the core problem.

---

## Not implemented in this version

The following are designed but **out of scope for this submission**:

- **PDF / Excel uploads.** The bonus item from the challenge brief. Design: server-side parsing (`pypdf` / `pdfplumber` for PDF, `openpyxl` → markdown tables for Excel), parsed content becomes user-scoped passages with stable IDs in a per-conversation namespace, exposed via `search_uploaded_files(query, k)` and `read_uploaded_passage(passage_id)` — same shape as the conviction tools, same retrieval and resolver pipeline. Uploaded passages are explicitly *user context* (lower trust than convictions) and tagged accordingly in the system prompt.
- **Hybrid retrieval (BM25 + multilingual embeddings + RRF).** v1 ships BM25-only; hybrid is the documented level-up under `ROADMAP.md` § B6, gated on a cross-language eval failure plus a conversation with the project owner.
- **Cross-encoder reranker** inside `search_convictions`. Further level-up beyond hybrid; gated on its own eval failure. See "Classic hybrid retrieval pipeline" above.
- **Postgres + pgvector.** v1 ships SQLite + a Python BM25 library; Postgres is the documented level-up under `ROADMAP.md` § B3, justified by concurrency or index-size pressure neither of which exists at 30 docs.
- **Anthropic Citations API** inside the Anthropic adapter (per-provider optimization for free `cited_text` and deterministic indices). Adapter slot exists; the optimization is not wired in.

## Implementation order (eval-driven)

1. **Passage parser + store.** Markdown → passages with stable IDs.
2. **Provider abstractions.** `LLMProvider` and `EmbeddingProvider` protocols. **OpenAI adapter first** for both LLM (`gpt-5`) and embeddings (`text-embedding-3-large`).
3. **`list_documents` + `read_passage` + `read_document_outline`** tools wired up.
4. **`search_convictions` — BM25-only over SQLite** with unicode-fold + accent-strip + lowercase normalization. Hybrid (BM25 + multilingual embeddings + RRF) is the documented level-up under `ROADMAP.md` § B6, gated on cross-language eval failure plus a conversation. See "Classic hybrid retrieval pipeline" in "Other architectures considered" for the full scaling story (corpus growth and audience expansion).
5. **Citation offset resolver.** Pure substring → `(start, end)` mapping; non-anchoring citations survive without a highlight. **Built before the agent loop** so every later step measures anchor rate from day one.
6. **Agent loop** with the system prompt enforcing all citation rules (Rule A, Rule B, clarifying-question, language mirroring). Multi-turn rewrite (`app/agent/rewrite.py`) is part of this step — prior assistant answers are never injected into the source-of-truth context.
7. **Disclaimer + audit log + cost tracking** wired into the orchestrator. SQLite is the storage; cost tracking is at three granularities (step, question, conversation).
8. **Eval suite.** See `TESTING.md`. Per-bucket floor: ≥ 3 questions, with Rule A and Rule B getting ≥ 4 each.
9. **Anthropic adapter (second provider)** — proves portability; demonstrates the architecture is provider-agnostic. May add Citations API as a per-adapter optimization.
10. **Optional promotion to hybrid retrieval** if eval shows BM25 misses cross-cutting / cross-language questions. Beyond hybrid: cross-encoder reranker, then Anthropic-style Contextual Retrieval. Each promotion is a conversation, not auto-triggered.
11. **Bonus (out of scope for v1): upload pipeline** — see `ASSUMPTIONS.md` § "Source formats" for the parser-interface design.

Each step should pass the eval before moving to the next. Promotion beyond step 4 (reranker, Contextual Retrieval, real vector store) is gated on documented eval failures, not speculation.
