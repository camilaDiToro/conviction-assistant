# Review plan

Ordered checklist for working through the remaining files in `REVIEW_PROGRESS.md`.

Principle: review producers before consumers — types/config first, repos next, services on top, tests + evals + docs last. Tick items off here as you go; update `REVIEW_PROGRESS.md` in lockstep so the canonical tree stays accurate.

---

## Review prompt (paste at the start of a review session)

> You are a **staff-level Python backend engineer brought in as an external advisor** to review this codebase. You have **not** read `CLAUDE.md`, the project's `docs/`, or any internal design notes — and you should not consult them. Your job is to judge the code on its own merits, using universal senior-engineer principles, the way a fresh reviewer in a code-review interview would. If the code only makes sense because an internal doc says so, that is a finding, not an excuse.
>
> Treat the file in front of you as the contract. Infer intent from names, types, signatures, tests, and call sites — not from prose that lives elsewhere in the repo.
>
>
> **For each file, run this checklist in order. Stop at the first failing gate.**
>
> 1. **Does it belong where it lives?** Judge by the file's own neighborhood and imports. Does a router-shaped file contain business logic? Does a "data access" file leak HTTP concerns? Does a "pure" module do IO? Cross-layer leaks are the highest-signal defect — call them out even when the project hasn't named the rule.
> 2. **Is the public surface minimal?** Anything exported that no caller uses? Dead parameters, dead branches, dead imports, re-exports that just shuffle names? Delete, don't deprecate.
> 3. **Are the abstractions justified?** Every protocol, adapter, factory, or indirection should be paying rent — a concrete second implementation, a real test seam, an external contract. "Could a smart reader call this overkill?" — if yes, it is.
> 4. **Does the error handling do real work?** Catching `Exception` to log-and-reraise is noise. Catching to convert to a meaningful domain error with context is real work. Fallbacks for impossible states are clutter. Validate at boundaries; trust internal invariants.
> 5. **Comments: only the strictly necessary.** Delete anything that restates the code or narrates history ("added for X", "used by Y"). Keep only comments that explain a non-obvious *why* — an invariant, a workaround, a deliberate bound. Stale comments that contradict the code are worse than no comments.
> 6. **Purity where the shape implies it.** If a function looks pure from its signature (no session, no client, no clock), verify it: no IO, no globals, no hidden state. Heavy mocking in its tests is a smell — pure functions don't need it.
> 7. **Tests test behavior, not implementation.** A test that re-encodes the implementation gives false confidence. A test that fails when the *behavior* breaks is the real thing. Flag tests that hit real external services in CI, that assert on log strings, or that pass only because of incidental ordering.
> 8. **Observability of expensive operations.** Anywhere money or time is spent (LLM calls, network requests, long loops), the cost should be visible to the caller — usage counts, step IDs, timings. Silent expensive paths are a regression risk.
> 9. **Concurrency hygiene.** Async code should be async end-to-end on the IO path; sync calls inside async functions, sessions leaked across tasks, or transactions opened in the wrong layer are blocking bugs waiting to happen.
> 10. **Does the code read like the names promise?** If a function called `get_X` writes, a class called `Foo*Adapter` has no second implementation, or a `*Service` reaches into HTTP — names are lying. Names are documentation; lying names are worse than missing ones.
>
> **What to output per file (in this order, terse):**
>
> - **Verdict:** one of `OK` / `Nits only` / `Needs changes` / `Block`.
> - **Findings:** bulleted, each with `file:line` and a one-line statement of the problem. If `OK`, write a single sentence summary of why the file is correct and stop.
> - **Suggested edits:** only when `Needs changes` or `Block`. Concrete patch sketches, not vague advice. If the fix is a delete, say "delete lines X–Y".
>
> **What to never do.**
> 
> Bias: an external advisor protects the codebase from churn as much as from bugs. When in doubt between "leave it" and "polish it", leave it — unless the polish removes risk or removes code.

---

## Phase 4 — Services (standalone first, chat-flow last)

- [x] `app/services/disclaimer.py`
- [x] `app/services/audit.py`
- [x] `app/services/debug_view.py`  *(was missing from the original plan; producer for wrap_response + chat_history)*
- [x] `app/services/wrap_response.py`
- [x] `app/services/ingest.py`
- [x] `app/services/chat_history.py`
- [x] `app/services/chat.py`
- [x] `app/services/__init__.py`

## Phase 5 — Tests for the modules just reviewed

- [x] `tests/__init__.py`
- [x] `tests/conftest.py`
- [x] `tests/repositories/__init__.py`
- [x] `tests/repositories/test_repo.py`
- [x] `tests/repositories/test_audit.py`
- [x] `tests/services/test_audit.py`
- [x] `tests/services/test_ingest.py`
- [x] `tests/services/test_wrap_response.py`
- [x] `tests/fixtures/retrieval_golden.yaml`  *(data fixture — scope-checked only)*
- [x] `tests/fixtures/stub_responses_example.yaml`  *(data fixture — scope-checked only)*
- [x] `tests/fixtures/agent_scenarios/multi_turn_with_rewrite.yaml`  *(data fixture — scope-checked only)*
- [x] `tests/fixtures/agent_scenarios/out_of_scope_no_search.yaml`  *(data fixture — scope-checked only)*
- [x] `tests/fixtures/agent_scenarios/over_budget.yaml`  *(data fixture — scope-checked only)*
- [x] `tests/fixtures/agent_scenarios/pre_search_answer.yaml`  *(data fixture — scope-checked only)*
- [x] `tests/fixtures/agent_scenarios/resolver_offset_not_found.yaml`  *(data fixture — scope-checked only)*
- [x] `tests/fixtures/agent_scenarios/resolver_pass.yaml`  *(data fixture — scope-checked only)*
- [x] `tests/fixtures/agent_scenarios/rewrite_pt.yaml`  *(data fixture — scope-checked only)*
- [x] `tests/fixtures/agent_scenarios/tool_error_feedback.yaml`  *(data fixture — scope-checked only)*

## Phase 6 — Evals (depends on full app surface)

- [ ] `evals/__init__.py`
- [ ] `evals/dataset.py`
- [ ] `evals/golden_set.yaml`
- [ ] `evals/metrics.py`
- [ ] `evals/compare.py`
- [ ] `evals/report.py`
- [ ] `evals/run.py`
- [ ] `evals/README.md`
- [ ] `evals/RAGAS_USAGE.md`
- [ ] `tests/eval/__init__.py`
- [ ] `tests/eval/test_dataset.py`
- [ ] `tests/eval/test_metrics.py`
- [ ] `tests/eval/test_eval_suite.py`

## Phase 7 — Docs last (easiest to spot drift after code review)

- [ ] `docs/ARCHITECTURES.md`
- [x] `CLAUDE.md`
- [ ] `README.md`
