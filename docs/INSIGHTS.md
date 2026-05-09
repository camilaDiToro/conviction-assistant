# Insights — Provider-Built RAG vs. Claude Code's "Just Tools" Approach

Research notes informing the architecture choice. Two parts:

1. **How the three frontier providers' built-in grounding stacks work**, with portability tradeoffs.
2. **How Claude Code works internally** — why it abandoned RAG for "agentic search," and what that means for this challenge.

---

## Part 1 — Provider-built grounding stacks (May 2026)

### Anthropic — Citations API + Files API + Search Tools

**Citations API** ([docs](https://platform.claude.com/docs/en/build-with-claude/citations))
- Pass documents directly in a `messages` request as `document` content blocks (plain text, PDF, or "custom content" for pre-chunked input).
- Set `citations.enabled: true` per document.
- The model returns multiple text blocks; each cited block has a `citations: [...]` field with `cited_text` (verbatim substring of the source) plus deterministic indices: `start_char_index`/`end_char_index` for plain text, page numbers for PDFs, content-block indices for custom content.
- `cited_text` does **not** count toward output tokens (free output) and `cited_text` passed back in subsequent turns does **not** count toward input tokens.
- Works with prompt caching (`cache_control` on the document block).
- **Incompatible with Structured Outputs** — citation blocks interleave with text and break strict JSON schema constraints.

**Files API** ([docs](https://platform.claude.com/docs/en/build-with-claude/files))
- Upload once, reference by `file_id` in any subsequent request. Files persist until deleted.
- Cleaner than re-uploading large PDFs every turn.

**Search-results content blocks** ([docs](https://docs.claude.com/en/docs/build-with-claude/search-results))
- A newer block type designed specifically so custom RAG apps can return retrieval hits in a shape Claude already knows how to cite from.

**Built-in search tools** ([advanced tool use](https://www.anthropic.com/engineering/advanced-tool-use))
- Out-of-the-box regex and BM25 search tools (no embeddings required).
- "Tool Search Tool" lets a model discover from thousands of tools without burning context.

**Claude Agent SDK / Managed Agents** ([analysis, Q2 2026](https://zylos.ai/research/2026-04-20-claude-agent-sdk-managed-agents-architecture))
- Default retrieval philosophy is **agentic search** — agent runs Bash-like commands (grep, find, tail) to load only relevant content. Vector search is only positioned as a fallback "when agentic search is insufficient."

**Portability cost:** the Citations API is the highest-fidelity option in any provider's stack, but it's Anthropic-only. Indices, response shape, and the `cited_text` mechanic don't exist in OpenAI or Google APIs. → fits behind the provider adapter, not as the architecture.

---

### OpenAI — File Search (in the Responses API)

**File Search tool** ([guide](https://developers.openai.com/api/docs/guides/tools-file-search), [Assistants tool reference](https://developers.openai.com/api/docs/assistants/tools/file-search))
- Upload files to a vector store (managed by OpenAI). Attach the store to a `file_search` tool call in the Responses API.
- Internally: query rewriting → parallel keyword + semantic search → reranking → answer.
- Built-in metadata filtering (added in the Responses API version).
- Pricing: **$2.50 per 1,000 calls + storage**.

**Migration note**
- The legacy **Assistants API is deprecated, sunset 2026-08-26.** ([FAQ](https://help.openai.com/en/articles/8550641))
- New work goes on the Responses API.

**Portability cost:** different shape from Anthropic. Citations are returned but not as char-indexed verbatim quotes — they're chunk-level references. Vector store is OpenAI-hosted, so portability means re-uploading + re-indexing per provider.

---

### Google — Vertex AI RAG Engine + Grounding with Vertex AI Search

**Vertex AI RAG Engine** ([blog](https://cloud.google.com/blog/products/ai-machine-learning/introducing-vertex-ai-rag-engine), [docs](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/grounding/ground-responses-using-rag))
- Fully managed RAG with native Gemini integration.
- Multi-source connectors: Cloud Storage, Google Drive, Slack, Jira, SharePoint.
- Configurable chunking, hybrid search, optional reranking.

**Grounding with Vertex AI Search** ([docs](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/grounding/grounding-with-vertex-ai-search))
- Connects Gemini to up to **10 data sources** at once.
- Combinable with Google Search grounding for live-web answers.

**Portability cost:** deepest tie-in to GCP. Heavy infrastructure choice if convictions ever live anywhere else.

---

### Side-by-side

| Capability | Anthropic | OpenAI | Google |
|---|---|---|---|
| Verbatim, char-indexed citations | **Yes** (Citations API) | No (chunk-level only) | No (chunk-level only) |
| `cited_text` free of output-token cost | **Yes** | n/a | n/a |
| Default retrieval philosophy | Agentic search (grep/BM25), embeddings as fallback | Managed hybrid index | Managed hybrid index |
| Hosted vector store | Optional / not required | Required | Required (Vertex AI Search) |
| Source connectors | DIY | DIY | Drive / GCS / Slack / Jira / SharePoint |
| Compatible with strict JSON schemas | No (with citations) | Yes | Yes |
| Cross-provider shape | n/a | n/a | n/a |

**Conclusion for the challenge:** every provider's hosted RAG breaks portability. Anthropic's Citations API is the most useful "advanced" feature *but* can't be required — it has to be a per-adapter optimization, not the architecture. The portable substrate is **tool use + JSON-schema responses**, which all three support uniformly.

---

## Part 2 — How Claude Code works (and why it matters here)

The recruiter cited Claude Code as inspiration. The single most important thing to know about Claude Code's design is that **it threw out RAG**.

### The agentic loop

From Anthropic's official docs ([How Claude Code works](https://code.claude.com/docs/en/how-claude-code-works)):

> When you give Claude a task, it works through three phases: **gather context**, **take action**, and **verify results**. These phases blend together. Claude uses tools throughout, whether searching files to understand your code, editing to make changes, or running tests to check its work.

> The agentic loop is powered by two components: models that reason and tools that act. Claude Code serves as the **agentic harness** around Claude: it provides the tools, context management, and execution environment that turn a language model into a capable coding agent.

The "harness" framing is the key idea. The model does the thinking; the harness gives it deterministic tools and a permission system. Per a [public architecture analysis](https://bits-bytes-nn.github.io/insights/agentic-ai/2026/03/31/claude-code-architecture-analysis.html), only ~1.6% of Claude Code's codebase is AI decision logic — the other ~98.4% is deterministic infrastructure (permission gates, context management, tool routing, recovery). Most of the "intelligence" comes from the model + the loop, not from clever ML around it.

### Tool categories (from the official docs)

| Category | What the tools do |
|---|---|
| File operations | Read files, edit code, create new files, rename and reorganize |
| **Search** | **Find files by pattern (Glob), search content with regex (Grep), explore codebases** |
| Execution | Run shell commands, start servers, run tests, use git |
| Web | Search the web, fetch documentation, look up error messages |
| Code intelligence | Type errors, jump to definition, find references |

**Search is grep + glob + read. No embeddings. No vector DB. No pre-built index.**

### Why Anthropic dropped RAG for Claude Code

Multiple sources, including team statements paraphrased in independent analyses ([SmartScope](https://smartscope.blog/en/ai-development/practices/rag-debate-agentic-search-code-exploration/), [Vadim's blog](https://vadim.blog/claude-code-no-indexing), [zerofilter](https://zerofilter.medium.com/why-claude-code-is-special-for-not-doing-rag-vector-search-agent-search-tool-calling-versus-41b9a6c0f4d9)), cite four reasons:

1. **Precision** — grep returns exact matches. Embeddings introduce fuzzy positives.
2. **Simplicity** — no index to build, no schema to maintain, no rerank model to swap.
3. **Freshness** — a pre-built index drifts during active editing. Live tools never drift.
4. **Privacy** — no data leaves the machine for embedding computation.

A fifth implicit reason: **as models get smarter, agentic search gets better automatically**. RAG quality depends on continuous engineering effort (better chunking, better embeddings, better rerankers).

There's a real trade-off — agentic search burns more tokens than vector retrieval ([Milvus's counter-argument](https://milvus.io/blog/why-im-against-claude-codes-grep-only-retrieval-it-just-burns-too-many-tokens.md)). The token cost is the price you pay for the four advantages above. For an interview-scale corpus, the math is fine.

### The broader "RAG obituary" thesis

Independent commentary frames this as part of a larger shift ([The RAG Obituary: Killed by Agents, Buried by Context Windows](https://www.nicolasbustamante.com/p/the-rag-obituary-killed-by-agents)): with strong models + tool use + larger context windows, classic chunked-vector RAG is increasingly the wrong default. The replacement isn't "do nothing" — it's "let the model search, with simple tools."

### How this maps onto the conviction-grounding problem

Translating Claude Code's pattern to this challenge:

| Claude Code | This project |
|---|---|
| `Glob` over filesystem | `list_documents()` over the conviction store |
| `Read` a file | `read_document(id)` or `read_passage(id)` |
| `Grep` for content | `search_convictions(query)` if eval shows ToC alone is insufficient |
| Three-phase loop (gather → act → verify) | Same loop, plus a deterministic substring verifier as the "verify" step |
| Permission system | Out-of-scope here, but cleanly maps to the system prompt's "must cite" rule |
| Plan mode / explicit reasoning | "First identify which documents are relevant, then answer" |

The architecture in `ARCHITECTURES.md` is essentially a domain-specialized Claude Code applied to investment convictions instead of source code: a small read-only tool surface (`list_documents` / `read_document_outline` / `search_convictions` / `read_passage`), a bounded gather→act→verify loop, and a deterministic citation verifier playing the role of Claude Code's permission system.

---

## Recommended reading & watching

### Official / primary

- **[How Claude Code works (official docs)](https://code.claude.com/docs/en/how-claude-code-works)** — agent loop, tool categories, context management, permissions.
- **[Anthropic — Advanced tool use](https://www.anthropic.com/engineering/advanced-tool-use)** — built-in regex/BM25 search tools, Tool Search Tool.
- **[Anthropic — Citations API docs](https://platform.claude.com/docs/en/build-with-claude/citations)** — verbatim, char-indexed citations.
- **[Anthropic — Contextual Retrieval](https://www.anthropic.com/news/contextual-retrieval)** — the technique to use *only if* you go full RAG.

### Videos

- **[Building Claude Code with Boris Cherny — Pragmatic Engineer](https://newsletter.pragmaticengineer.com/p/building-claude-code-with-boris-cherny)** — origin story, internal usage patterns, design choices (newsletter article with linked podcast).
- **[Even Anthropic Engineers Use This Claude Code Workflow (YouTube)](https://www.youtube.com/watch?v=ASAaKhK1B5w)** — the workflow video.
- **[Two Anthropic engineers spent 24 minutes exposing every Claude Code feature you didn't know existed (YouTube)](https://www.youtube.com/watch?v=x7m_Mr14KIc)** — recent deep dive on internals.
- **[How Anthropic Employees ACTUALLY Use Claude Code (YouTube)](https://www.youtube.com/watch?v=pRfIWmddRsE)** — how non-technical staff at Anthropic use it.
- **[How Anthropic uses Claude in Product Engineering (YouTube)](https://www.youtube.com/watch?v=ma7oe_5h0ag)** — engineer Chuma Kabaghe walkthrough.
- **[How Boris uses Claude Code (companion site)](https://howborisusesclaudecode.com/)** — Boris Cherny's own workflow notes.
- **[How to Use Claude Code Like the People Who Built It — Every podcast](https://every.to/podcast/how-to-use-claude-code-like-the-people-who-built-it)** — origin and tips from the team.

### Architecture analyses (third-party, but well-researched)

- **[Claude Code Architecture Analysis](https://bits-bytes-nn.github.io/insights/agentic-ai/2026/03/31/claude-code-architecture-analysis.html)** — the "1.6% AI logic / 98.4% deterministic" breakdown.
- **[Claude Code Doesn't Index Your Codebase. Here's What It Does Instead.](https://vadim.blog/claude-code-no-indexing)** — clear explanation of agentic search.
- **[Why Claude Code Abandoned RAG for Agentic Search](https://zenn.dev/karamage/articles/2514cf04e0d1ac?locale=en)** — the four reasons in depth.
- **[Settling the RAG Debate (SmartScope)](https://smartscope.blog/en/ai-development/practices/rag-debate-agentic-search-code-exploration/)** — agentic vs. vector retrieval analysis.
- **[Why Cursor, Claude Code, and Devin Use grep, Not Vectors](https://www.mindstudio.ai/blog/is-rag-dead-what-ai-agents-use-instead)** — wider industry context.
- **[The RAG Obituary: Killed by Agents, Buried by Context Windows](https://www.nicolasbustamante.com/p/the-rag-obituary-killed-by-agents)** — the broader thesis.
- **[Claude Code Harness: Runtime Architecture (2026 Guide)](https://pasqualepillitteri.it/en/news/1892/claude-code-harness-runtime-architecture-2026-guide)** — harness framing.
- **[Inside Claude Code: The Architecture That Makes AI Actually Do the Work](https://qubytes.substack.com/p/claude-code-architecture-explained)** — accessible overview.

### Counter-points worth reading

- **[Why I'm Against Claude Code's Grep-Only Retrieval (Milvus blog)](https://milvus.io/blog/why-im-against-claude-codes-grep-only-retrieval-it-just-burns-too-many-tokens.md)** — the "agentic search burns too many tokens" critique. Worth knowing for the interview discussion.

### Provider-built RAG references

- **[OpenAI File Search guide](https://developers.openai.com/api/docs/guides/tools-file-search)** + **[Assistants File Search reference](https://developers.openai.com/api/docs/assistants/tools/file-search)**.
- **[Vertex AI RAG Engine — Google Cloud blog](https://cloud.google.com/blog/products/ai-machine-learning/introducing-vertex-ai-rag-engine)**.
- **[Grounding with Vertex AI Search docs](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/grounding/grounding-with-vertex-ai-search)**.
- **[Vertex AI Search vs RAG Engine — practical comparison](https://docs.digitalden.cloud/posts/vertex-ai-search-vs-rag-engine/)**.

### Eval / faithfulness

- **[RAGAS, TruLens, DeepEval comparison (Atlan, 2026)](https://atlan.com/know/llm-evaluation-frameworks-compared/)**.
- **[RAG Evaluation Metrics & Frameworks 2026](https://blog.premai.io/rag-evaluation-metrics-frameworks-testing-2026/)**.
- **[AAAI 2026 — RAG over-refusal paper summary](https://www.bohrium.com/en/blog/research-notes/aaai-2026-retrieval-augmented-models-dont-know/)**.

---

## What carries over to the design decisions

The takeaways that directly inform `ARCHITECTURES.md`:

1. **Don't build a retrieval pipeline.** The interviewer's hint and Claude Code's design point the same way: tools + a strong model + a verifier outperforms hand-engineered retrieval at this scale.
2. **The harness is most of the value.** Code quality the interviewer will see lives in the deterministic parts: passage parser, tool definitions, schema validation, substring verifier, provider abstraction. Make those clean.
3. **Provider-native grounding is for adapters, not architecture.** Anthropic's Citations API is excellent — use it from the Anthropic adapter to get free output tokens and guaranteed valid indices. Don't depend on it.
4. **Three-phase loop is the right mental model:** *Gather* (list docs / read relevant ones) → *Act* (compose answer with citations) → *Verify* (substring-match every quote; reject or repair if it fails).
5. **Token cost is the price of agentic search.** Acknowledge it in the README, mitigate with prompt caching on the system prompt and stable parts of the conversation.
