# Review progress

Tracking which modules + tests have been reviewed file-by-file.

Legend: `[x]` = reviewed, `[ ]` = pending.

```
decade-ai-challenge/
├── [x] .dockerignore
├── [ ] .env.example
├── [x] .github/workflows/sync-to-hf.yml
├── [x] .gitignore
├── [x] AI_CHALLENGE.md
├── [ ] CLAUDE.md
├── [x] Dockerfile
├── [ ] README.md
├── [x] alembic.ini
├── [x] pyproject.toml
├── [x] uv.lock
│
├── alembic/                             [ ] re-review pending after recent edits
│   ├── [ ] env.py                       — target_metadata=Base.metadata as drift safety net; sync driver for SQLite v1
│   ├── [x] script.py.mako
│   └── versions/
│       └── [ ] 0001_initial_schema.py   — absorbed former 0002; downgrade raises NotImplementedError
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
│   ├── config/
│   │   ├── [ ] __init__.py
│   │   ├── [ ] db.py
│   │   └── [ ] settings.py
│   │
│   ├── models/
│   │   ├── [ ] __init__.py
│   │   ├── [ ] audit.py
│   │   ├── [ ] base.py
│   │   └── [ ] passage.py
│   │
│   ├── providers/
│   │   ├── [ ] __init__.py
│   │   ├── [ ] base.py
│   │   ├── [ ] factory.py
│   │   ├── [ ] openai.py
│   │   ├── [ ] stub.py
│   │   └── [ ] text_repair.py
│   │
│   ├── repositories/
│   │   ├── [ ] __init__.py
│   │   ├── [ ] audit.py
│   │   ├── [ ] introspection.py
│   │   └── [ ] passages.py
│   │
│   ├── retrieval/                       [x] reviewed
│   │   ├── [x] __init__.py
│   │   ├── [x] base.py
│   │   ├── [x] bm25.py
│   │   ├── [x] registry.py
│   │   └── [x] snippet.py
│   │
│   ├── schemas/
│   │   ├── [ ] __init__.py
│   │   ├── [ ] ingest.py
│   │   └── [ ] passage.py
│   │
│   └── services/
│       ├── [ ] __init__.py
│       ├── [ ] audit.py
│       ├── [ ] chat.py
│       ├── [ ] chat_history.py             — extracted in api-cleanup PR; reconstructs ConversationMessage / ChatCitation / UsageSummary from audit_log rows
│       ├── [ ] disclaimer.py
│       ├── [ ] ingest.py
│       ├── [ ] wrap_response.py
│       └── parser/                      [x] reviewed
│           ├── [x] __init__.py
│           ├── [x] markdown.py
│           ├── [x] registry.py
│           └── [x] text.py
│
├── convictions/                         (30 markdown corpus files — not code)
│
├── docs/
│   ├── [ ] ARCHITECTURES.md
│   ├── [ ] ASSUMPTIONS.md
│   ├── [ ] DEPLOY.md
│   ├── [ ] MODEL_CONFIG.md
│   ├── [ ] SCALE_NOTES.md
│   └── [ ] TESTING.md
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
    ├── [ ] __init__.py
    ├── [ ] conftest.py
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
    ├── api/
    │   ├── [ ] __init__.py
    │   ├── [ ] test_admin.py
    │   ├── [ ] test_chat.py
    │   ├── [ ] test_chat_history.py
    │   ├── [ ] test_config.py
    │   └── [ ] test_conversations.py
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
    │       ├── [ ] basic_search.yaml
    │       ├── [ ] clarifying.yaml
    │       ├── [ ] multi_turn_with_rewrite.yaml
    │       ├── [ ] out_of_scope_no_search.yaml
    │       ├── [ ] over_budget.yaml
    │       ├── [ ] pre_search_answer.yaml
    │       ├── [ ] resolver_offset_not_found.yaml
    │       ├── [ ] resolver_pass.yaml
    │       ├── [ ] rewrite_pt.yaml
    │       └── [ ] tool_error_feedback.yaml
    │
    ├── providers/
    │   ├── [ ] __init__.py
    │   ├── [ ] test_factory.py
    │   ├── [ ] test_openai_adapter.py
    │   └── [ ] test_stub.py
    │
    ├── repositories/
    │   ├── [ ] __init__.py
    │   ├── [ ] test_audit.py
    │   └── [ ] test_repo.py
    │
    ├── retrieval/                       [x] reviewed (simplified)
    │   ├── [x] __init__.py
    │   ├── [x] test_bm25.py             — parametrized _normalize, dropped k-cap test
    │   ├── [x] test_protocol_conformance.py — dropped weak no-match test
    │   └── [x] test_snippet.py
    │
    └── services/
        ├── [ ] test_audit.py
        ├── [ ] test_ingest.py
        ├── [ ] test_wrap_response.py
        └── parser/                      [x] reviewed
            ├── [x] __init__.py
            ├── [x] test_corpus_snapshot.py
            ├── [x] test_markdown.py
            └── [x] test_registry.py
```

## Notes on simplifications applied

- **`tests/retrieval/test_bm25.py`**: merged `test_normalize_strips_diacritics_for_pt` + `..._for_es` into one `@pytest.mark.parametrize`'d test (3 cases). Dropped `test_index_search_k_capped_at_corpus_size` — exercised `bm25s` library behavior, not project code.
- **`tests/retrieval/test_protocol_conformance.py`**: dropped `test_no_match_query_returns_empty` — only asserted `isinstance(hits, list)`, no real signal.
- **`app/agent/resolver/substring.py`**: extracted `_resolve_one(citation, passage)` so the four `CitationResolution(...)` branches share one provenance dict — cuts the function from ~60 lines of duplicated constructors to ~25.
- **`tests/agent/resolver/test_substring.py`**: collapsed 11 tests → 7 by removing direct `resolve_citation` tests (covered transitively by `resolve_answer`) and the no-citations edge case (trivial empty-comprehension path).
- **`app/agent/loop.py`**: split `_agent_loop` into short helpers (`_build_initial_messages`, `_llm_turn`, `_handle_tool_branch`, `_parse_output`, `_needs_search_first`, `_append_search_reminder`, `_resolve_answer`); orchestrator is now a 30-line readable loop.

## Suggested review order

1. `app/agent/resolver/` — deterministic offset resolver (architecture's grounding guarantee)
2. `app/agent/tools/` — read-only tool surface the agent calls
3. `app/agent/` core (`loop.py`, `rewrite.py`, `tool_dispatch.py`, `dedupe.py`)
4. `app/providers/` — LLM/Embedding abstraction + adapters
5. `app/api/` + `app/services/` — HTTP boundary and orchestration
6. `app/repositories/` + `app/models/` + `alembic/` — persistence layer
