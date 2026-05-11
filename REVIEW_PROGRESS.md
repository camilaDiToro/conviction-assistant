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
│   │   ├── [ ] dedupe.py
│   │   ├── [x] loop.py                    — split _agent_loop into short helpers; orchestrator is a 30-line readable loop
│   │   ├── [x] rewrite.py                  — only stage that consumes history (loop quarantine), language detection, structured output
│   │   ├── [ ] schemas.py
│   │   ├── [ ] tool_dispatch.py
│   │   ├── prompts/
│   │   │   ├── [x] rewrite.md
│   │   │   └── [ ] system.md
│   │   ├── resolver/                   [x] reviewed (simplified)
│   │   │   ├── [x] __init__.py             — shortened module doc
│   │   │   ├── [x] base.py                 — corrected invariants doc, trimmed class docs
│   │   │   └── [x] substring.py            — dried resolve_answer via _resolve_one + shared provenance
│   │   └── tools/
│   │       ├── [ ] __init__.py
│   │       ├── [ ] context.py
│   │       ├── [ ] list_documents.py
│   │       ├── [ ] read_document_outline.py
│   │       ├── [ ] read_passage.py
│   │       ├── [ ] registry.py
│   │       └── [ ] search_convictions.py
│   │
│   ├── api/
│   │   ├── [ ] __init__.py
│   │   ├── [ ] admin.py
│   │   ├── [ ] auth.py
│   │   ├── [x] chat.py                         — thin handler: token gate, deps for session/llm, retriever from app.state with 503 guard
│   │   ├── [ ] chat_history.py
│   │   ├── [ ] config.py
│   │   ├── [ ] conversations.py
│   │   ├── [ ] deps.py
│   │   ├── [ ] health.py
│   │   └── [ ] schemas.py
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
│       ├── [ ] conversations.py
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
├── frontend/
│   ├── [ ] .env.example
│   ├── [ ] .gitignore
│   ├── [ ] index.html
│   ├── [ ] package.json
│   ├── [ ] package-lock.json
│   ├── [ ] postcss.config.js
│   ├── [ ] tailwind.config.ts
│   ├── [ ] tsconfig.app.json
│   ├── [ ] tsconfig.json
│   ├── [ ] tsconfig.node.json
│   ├── [ ] vite.config.ts
│   ├── public/
│   │   └── [ ] decade-mark.svg
│   └── src/
│       ├── [ ] App.tsx
│       ├── [ ] main.tsx
│       ├── [ ] index.css
│       ├── [ ] vite-env.d.ts
│       ├── components/
│       │   ├── [ ] Callout.tsx
│       │   ├── [ ] CodeBlock.tsx
│       │   ├── [ ] GridMark.tsx
│       │   ├── [ ] PassageCard.tsx
│       │   ├── [ ] Section.tsx
│       │   ├── [ ] Sidebar.tsx
│       │   └── [ ] Spec.tsx
│       ├── data/
│       │   ├── [ ] decisions.ts
│       │   ├── [ ] exampleConviction.ts
│       │   ├── [ ] roadmap.ts
│       │   └── [ ] toolSchemas.ts
│       ├── features/
│       │   ├── chat/
│       │   │   ├── [ ] AccessGate.tsx
│       │   │   ├── [ ] ChatPage.tsx
│       │   │   ├── [ ] CitationModal.tsx
│       │   │   ├── [ ] DebugDrawer.tsx
│       │   │   ├── [ ] MessageList.tsx
│       │   │   └── [ ] Sidebar.tsx
│       │   ├── design/
│       │   │   ├── [ ] AgentLoopPage.tsx
│       │   │   ├── [ ] CorpusPage.tsx
│       │   │   ├── [ ] DesignLayout.tsx
│       │   │   ├── [ ] LayeringPage.tsx
│       │   │   ├── [ ] OverviewPage.tsx
│       │   │   ├── [ ] ProvidersPage.tsx
│       │   │   ├── [ ] ResolverPage.tsx
│       │   │   ├── [ ] RetrievalPage.tsx
│       │   │   ├── [ ] TiersPage.tsx
│       │   │   └── [ ] ToolsPage.tsx
│       │   └── home/
│       │       └── [ ] LandingPage.tsx
│       └── lib/
│           ├── [ ] access-gate.ts
│           ├── [ ] api.ts
│           ├── [ ] bm25.ts
│           ├── [ ] resolver.ts
│           └── [ ] types.ts
│
├── scripts/
│
└── tests/
    ├── [ ] __init__.py
    ├── [ ] conftest.py
    │
    ├── agent/
    │   ├── [ ] __init__.py
    │   ├── [ ] conftest.py
    │   ├── [ ] test_dedupe.py
    │   ├── [ ] test_loop_with_resolver.py
    │   ├── [ ] test_loop_with_stub.py
    │   ├── [ ] test_rewrite.py
    │   ├── resolver/                    [x] reviewed (simplified)
    │   │   ├── [x] __init__.py
    │   │   └── [x] test_substring.py     — collapsed to 7 tests through resolve_answer; kept property test + smart-quote guard
    │   └── tools/
    │       ├── [ ] __init__.py
    │       ├── [ ] test_search_convictions.py
    │       └── [ ] test_simple_tools.py
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
7. `frontend/src/`
