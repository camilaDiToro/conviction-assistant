# Review progress

Tracking which modules + tests have been reviewed file-by-file.

Legend: `[x]` = reviewed, `[ ]` = pending.

```
decade-ai-challenge/
├── [x] .dockerignore
├── [x] .env.example                    — supported OPENAI_MODEL list (6 entries) + reasoning_effort intersection note
├── [x] .github/workflows/sync-to-hf.yml
├── [x] .gitignore
├── [x] AI_CHALLENGE.md
├── [x] CLAUDE.md
├── [x] Dockerfile
├── [ ] README.md
├── [x] alembic.ini
├── [x] pyproject.toml
├── [x] uv.lock
│
├── alembic/                             [x] reviewed
│   ├── [x] env.py                       — target_metadata=Base.metadata as drift safety net; sync driver for SQLite v1
│   ├── [x] script.py.mako
│   └── versions/
│       └── [x] 0001_initial_schema.py   — absorbed former 0002; downgrade raises NotImplementedError; ck_audit_log_kind now mirrored on ORM
│
├── app/
│   ├── [x] __init__.py                     — empty package marker
│   ├── [x] errors.py                       — clean DomainError hierarchy, one-way dependency from API
│   ├── [x] main.py                         — lifespan order, fail-fast tokens, domain→HTTP handlers, SPA mount
│   │
│   ├── agent/
│   │   ├── [x] __init__.py                — public surface: `run` + structured output models; rewrite stage is the conversation-memory quarantine
│   │   ├── [x] audit.py                   — step-record builders (llm_call / tool_call / resolver) + resolver-side passage fetch adapter
│   │   ├── [x] dedupe.py                  — collapse duplicate citations by passage_id, remap inline [N] markers in answer text
│   │   ├── [x] loop.py                    — split _agent_loop into short helpers; orchestrator is a 30-line readable loop
│   │   ├── [x] rewrite.py                  — only stage that consumes history (loop quarantine), language detection, structured output
│   │   ├── [x] schemas.py                 — pydantic models + hand-written JSON schemas (flat+discriminator pattern bc openai strict ≠ oneOf)
│   │   ├── [x] tool_dispatch.py             — single entry execute_tool: lookup TOOLS, run via ToolEntry.func, catch DomainError/TypeError to JSON {"error":...}, serialize Pydantic results
│   │   ├── prompts/
│   │   │   ├── [x] rewrite.md
│   │   │   └── [x] system.md
│   │   ├── resolver/                   [x] reviewed (simplified)
│   │   │   ├── [x] __init__.py             — shortened module doc
│   │   │   ├── [x] base.py                 — corrected invariants doc, trimmed class docs
│   │   │   └── [x] substring.py            — dried resolve_answer via _resolve_one + shared provenance
│   │   └── tools/
│   │       ├── [x] __init__.py                — re-exports tools, ToolDefinitions, TOOLS registry, ToolContext/ToolEntry
│   │       ├── [x] context.py                 — DI seam: ToolContext(session, retriever) + ToolEntry(definition, func), both frozen dataclasses
│   │       ├── [x] list_documents.py          — corpus table of contents (DocSummary list ordered by document_id)
│   │       ├── [x] read_document_outline.py   — one document's heading tree + metadata; raises DocumentNotFoundError
│   │       ├── [x] read_passage.py            — full text of N passages by ID, order-preserving; raises PassageNotFoundError
│   │       ├── [x] registry.py                 — hand-written JSON schemas (OpenAI strict-mode compliant) + ToolDefinitions + TOOLS dict
│   │       └── [x] search_convictions.py      — BM25 over corpus via ctx.retriever; EmptyQueryError on blank input
│   │
│   ├── api/                                [x] reviewed
│   │   ├── [x] __init__.py
│   │   ├── [x] admin.py
│   │   ├── [x] auth.py                         — hmac.compare_digest + fail-closed on missing token; two-token model
│   │   ├── [x] chat.py                         — thin handler; session / llm / retriever via deps
│   │   ├── [x] chat_history.py                 — three GET endpoints; delegates reconstruction to services/chat_history
│   │   ├── [x] config.py                       — surfaces server-selected chat model (X-Chat-Token)
│   │   ├── [x] deps.py                         — get_llm_provider_dep + get_retriever_dep seams for tests
│   │   ├── [x] health.py                       — liveness probe (Docker / HF Space)
│   │   └── [x] schemas.py                      — StrictModel base; ConversationMessage as discriminated union
│   │
│   ├── config/                          [x] reviewed
│   │   ├── [x] __init__.py                — re-exports Settings + singleton
│   │   ├── [x] db.py                      — async engine + module-scope session factory; sync migrate() for Alembic
│   │   └── [x] settings.py                — pydantic-settings BaseSettings; narrowed llm_provider to Literal["openai"] (anthropic adapter not shipped)
│   │
│   ├── models/                          [x] reviewed
│   │   ├── [x] __init__.py                — re-exports Base + ORM classes
│   │   ├── [x] audit.py                   — append-only ORM; payload/usage are JSON-encoded Text columns
│   │   ├── [x] base.py                    — single DeclarativeBase subclass
│   │   └── [x] passage.py                 — heading_path stored as JSON Text; bridge lives in repositories/passages.py
│   │
│   ├── providers/                       [x] reviewed (simplified)
│   │   ├── [x] __init__.py                — re-exports LLMProvider/Message/types + get_llm_provider
│   │   ├── [x] base.py                     — LLMProvider protocol; ReasoningEffort = low|medium|high (allowlist intersection)
│   │   ├── [x] factory.py                  — _SUPPORTED_MODEL_PREFIXES allowlist; rejects unknown OPENAI_MODEL up-front
│   │   ├── [x] openai.py                   — single class targeting Responses API; chat completions path removed
│   │   ├── [x] stub.py                     — StubLLM mirror of the protocol (StubEmbedder removed)
│   │   └── [x] text_repair.py              — gpt-5-mini unicode-escape repair (kept; defensive + cheap)
│   │
│   ├── repositories/                       [x] reviewed
│   │   ├── [x] __init__.py                — docstring refreshed to mention both passages.py and audit.py
│   │   ├── [x] audit.py                   — TypedDict rows; rowid order on per-question reads is intentional (Windows clock granularity)
│   │   └── [x] passages.py                — upsert_many docstring narrowed to whole-corpus/whole-document contract
│   │
│   ├── retrieval/                       [x] reviewed
│   │   ├── [x] __init__.py
│   │   ├── [x] base.py
│   │   ├── [x] bm25.py
│   │   ├── [x] registry.py
│   │   └── [x] snippet.py
│   │
│   ├── schemas/                         [x] reviewed
│   │   ├── [x] __init__.py                — re-exports schema models alphabetically
│   │   ├── [x] ingest.py                  — plain Pydantic response model for /admin/ingest
│   │   └── [x] passage.py                 — Passage / DocSummary / Heading / DocumentOutline / PassageHit; from_attributes=True throughout
│   │
│   └── services/                          [x] reviewed
│       ├── [x] __init__.py                — docstring states services raise DomainError, never HTTPException
│       ├── [x] audit.py                   — best-effort writer; commits on success, rolls back on failure
│       ├── [x] chat.py                    — thin orchestrator: IDs → agent → wrap → persist audit
│       ├── [x] chat_history.py            — reconstructs ConversationMessage / ChatCitation / UsageSummary from audit_log rows
│       ├── [x] debug_view.py              — off-plan find; shared live + historical debug-step formatter
│       ├── [x] disclaimer.py              — three frozen strings keyed by Language
│       ├── [x] ingest.py                  — parser → repo orchestrator inside one session.begin()
│       ├── [x] wrap_response.py           — pure AgentResult → wire response + audit summary mapping
│       └── parser/                      [x] reviewed
│           ├── [x] __init__.py
│           ├── [x] markdown.py
│           ├── [x] registry.py
│           └── [x] text.py
│
├── convictions/                         (30 markdown corpus files — not code)
│
├── docs/
│   └── [ ] ARCHITECTURES.md
│
├── evals/
│   ├── [ ] __init__.py
│   ├── [ ] README.md
│   ├── [ ] RAGAS_USAGE.md
│   ├── [ ] compare.py
│   ├── [ ] dataset.py
│   ├── [ ] golden_set.yaml
│   ├── [ ] metrics.py
│   ├── [ ] report.py
│   └── [ ] run.py
│
├── frontend/                            (out of review scope)
│
├── scripts/
│
└── tests/
    ├── [x] __init__.py                     — empty package marker
    ├── [x] conftest.py                     — sets startup-token env defaults so lifespan token check survives test imports
    │
    ├── agent/                              [x] reviewed
    │   ├── [x] __init__.py
    │   ├── [x] conftest.py                — autouse fixture patches passages_repo.get_many for loop tests under tests/agent/ only
    │   ├── [x] test_answer_output_invariants.py  — 6 cases over the @model_validator branches on AnswerOutput
    │   ├── [x] test_dedupe.py             — 4 tests covering happy path, no-op, out-of-range markers, empty
    │   ├── [x] test_loop_with_resolver.py
    │   ├── [x] test_loop_with_stub.py     — protocol invariants (no assistant text in loop, ≥1 search, budget cap, invariant retry)
    │   ├── [x] test_rewrite.py
    │   ├── [x] test_token_totals.py       — AgentResult.token_totals sums llm_call usages only
    │   ├── resolver/                    [x] reviewed (simplified)
    │   │   ├── [x] __init__.py
    │   │   └── [x] test_substring.py     — collapsed to 7 tests through resolve_answer; kept property test + smart-quote guard
    │   └── tools/                       [x] reviewed
    │       ├── [x] __init__.py
    │       ├── [x] test_search_convictions.py  — golden-set recall@5 floors + p95 latency + empty-query guard
    │       └── [x] test_simple_tools.py        — pure-function tests for list_documents / read_document_outline / read_passage + registry sanity
    │
    ├── api/                                [x] reviewed
    │   ├── [x] __init__.py
    │   ├── [x] test_admin.py                — happy path + missing-dir → 400; doesn't cover admin-token auth
    │   ├── [x] test_chat.py                 — StubLLM + real SQLite; happy path, 401/503 auth, ES/PT disclaimers, audit rows, supplied conv_id, clarifying branch
    │   ├── [x] test_chat_history.py         — list/load/steps endpoints; offset round-trip (passage_text[start:end]); cross-turn order
    │   └── [x] test_config.py               — happy path + missing/wrong token → 401
    │
    ├── eval/
    │   ├── [ ] __init__.py
    │   ├── [ ] test_dataset.py
    │   ├── [ ] test_eval_suite.py
    │   └── [ ] test_metrics.py
    │
    ├── fixtures/
    │   ├── [ ] retrieval_golden.yaml
    │   ├── [ ] stub_responses_example.yaml
    │   └── agent_scenarios/
    │       ├── [x] basic_search.yaml                — 4-turn stub: rewrite → search → read_passage → answer with citation; used by tests/api/test_chat + test_chat_history
    │       ├── [x] clarifying.yaml                  — stub returning kind=clarifying_question; used by tests/api/test_chat::test_chat_clarifying_branch
    │       ├── [ ] multi_turn_with_rewrite.yaml
    │       ├── [ ] out_of_scope_no_search.yaml
    │       ├── [ ] over_budget.yaml
    │       ├── [ ] pre_search_answer.yaml
    │       ├── [ ] resolver_offset_not_found.yaml
    │       ├── [ ] resolver_pass.yaml
    │       ├── [ ] rewrite_pt.yaml
    │       └── [ ] tool_error_feedback.yaml
    │
    ├── providers/                       [x] reviewed (simplified)
    │   ├── [x] __init__.py
    │   ├── [x] test_factory.py             — parametrized allowlist/rejection cases; one configure_openai fixture
    │   ├── [x] test_openai_adapter.py      — one round-trip per layer (messages, response, end-to-end), parametrized error cases
    │   └── [x] test_stub.py                 — protocol mirror + YAML loader
    │
    ├── repositories/                       [x] reviewed
    │   ├── [x] __init__.py                 — empty package marker
    │   ├── [x] test_audit.py               — insert+fetch round-trip + empty-conversation
    │   └── [x] test_repo.py                — integration over real per-test SQLite; covers round-trip, outline, idempotent re-ingest, orphan delete, unicode, real corpus
    │
    ├── retrieval/                       [x] reviewed (simplified)
    │   ├── [x] __init__.py
    │   ├── [x] test_bm25.py             — parametrized _normalize, dropped k-cap test
    │   ├── [x] test_protocol_conformance.py — dropped weak no-match test
    │   └── [x] test_snippet.py
    │
    └── services/                           [x] reviewed
        ├── [x] test_audit.py               — three tests: row count, conversation isolation, failure swallowing via monkeypatched repo
        ├── [x] test_ingest.py               — missing-dir / empty / happy / re-ingest-with-rename / real-corpus regression canary (423 passages)
        ├── [x] test_wrap_response.py        — pure-function tests for anchored / clarifying / non-anchoring citation branches
        └── parser/                      [x] reviewed
            ├── [x] __init__.py
            ├── [x] test_corpus_snapshot.py
            ├── [x] test_markdown.py
            └── [x] test_registry.py
```