# B7 — decisions log

Per-step decisions for ROADMAP B7 (agent orchestrator: bounded loop + system prompt + structured output + multi-turn rewrite). Companion to the architectural rules pinned in `docs/ARCHITECTURES.md` § "Loop bounds" and § "Conversation memory". This file captures the *step-local* choices — and the architectural research that produced them — that don't rise to architecture but should be visible to a reviewer.

For the high-level rules (single-LLM-point, layering, tool surface, response contract), read `docs/ARCHITECTURES.md` first.

---

## Why the swap (B7 ↔ B8 reorder)

The original roadmap built **B7 = Citation verifier** before **B8 = Agent orchestrator**, on the rationale that "every later step measures verifier pass rate from day one." The user reordered: agent first, verifier second.

**Trade-off accepted:** B7's tests don't measure verifier pass rate. The agent orchestrator ships with structured output but no grounding check.

**Trade-off bought:** the verifier step (now B8) retrofits the verifier *and* the retry-once-with-feedback path inside `app/agent/loop.py` against a real loop instead of speculating against a stub. The retry path is the verifier's most expensive piece of integration — building it against a real surface beats designing it twice.

The numerical labels in `docs/ROADMAP.md` were preserved (B7 stays B7, B8 stays B8) — only the *contents* swap. B9's `Depends on: B8` line is unchanged in spirit (B8 is now the verifier-enabled agent).

---

## Shape at a glance

```text
                    user_message + history
                              │
                              ▼
                       app/agent/__init__.run()
                              │
                ┌─────────────┴─────────────┐
                │ history empty?            │
                ▼                           ▼
         pass-through                rewrite_question()
                                      (1 minimal LLM call,
                                       sees prior assistant text,
                                       outputs self-contained question)
                              │
                              ▼
                        _agent_loop()
                ┌───── for _ in MAX_ITERATIONS:
                │       │
                │       ▼
                │   llm.generate(messages, tools=TOOLS, schema=AGENT_OUTPUT)
                │       │
                │       ├── tool_calls? ──→ pre-execution budget check
                │       │                  → asyncio.gather(execute each)
                │       │                  → append tool messages
                │       │                  → continue
                │       │
                │       └── parsed? ──→ AgentOutput.validate
                │                       └── lower-bound check (≥1 search)
                │                       └── return
                ▼
        AgentResult { output, rewritten_question, steps, counts }
```

The whole thing respects three guard rails the rest of the project depends on:

1. **Single LLM point** — every model call goes through `llm.generate()` from the provider abstraction. `git grep "from openai" app/` returns one file: `app/providers/openai.py`.
2. **No `HTTPException`, no `os.getenv` outside `app/config/`** — the agent raises `AgentError` (a `DomainError` subclass); settings come from `app.config.settings`. CI-greppable.
3. **Conversation-memory quarantine** — prior assistant text never reaches the loop's `messages` list. Asserted by `test_multi_turn_no_assistant_text_in_loop`.

---

## Multi-turn handling — what we chose and why

The architectural rule (`docs/ARCHITECTURES.md` § Conversation memory) is hard:

> **Prior assistant answers are never injected into the source-of-truth context.** Each turn runs fresh tool calls. Prior conversation is used only to rewrite or contextualize the current question.

Three patterns honor that rule. We compared them before committing.

### Pattern 1 — Compaction (Claude Code's pattern)

**What it is.** Each new session starts fresh; *within* a session the model sees the full conversation (user + assistant + tool results), with a 5-layer compaction pipeline running before every model call (budget reduction → snip → microcompact → context collapse → auto-compact). Thinking blocks are auto-stripped.

Sources:
- [How Claude Code works (official docs)](https://code.claude.com/docs/en/how-claude-code-works)
- [Compaction (Claude API docs)](https://platform.claude.com/docs/en/build-with-claude/compaction)

**Why it's the wrong fit for grounded RAG.** Claude Code is a *coding agent* where the prior assistant turn is the work product — "what was decided" — and is **trusted**. Importing the same pattern here would let an earlier hallucination contaminate the next turn's context, then get cited by an unsuspecting verifier (the substring verifier checks quotes against passages, not against prior assistant text). Different trust model → different solution.

### Pattern 2 — Full-history sessions (OpenAI Agents SDK pattern)

**What it is.** `SQLiteSession` / `OpenAIConversationsSession` automatically persist the full prior conversation; the agent sees every turn. No built-in rewriting. Same trust model as Claude Code.

Source:
- [OpenAI Agents Python — Sessions](https://github.com/openai/openai-agents-python/blob/main/docs/sessions/index.md)

**Why it's the wrong fit.** Same as Pattern 1 — assistant text is treated as authoritative context, which would let earlier hallucinations propagate.

### Pattern 3 — Selective query rewriting (2026 RAG community consensus)

**What it is.** A separate, isolated LLM call rewrites the user's new question into a self-contained question by resolving referents against prior turns. The rewrite call *can* see prior assistant text (its only job is to resolve "and what about LCAs?" against "we were talking about CDB taxation"); the agent loop *cannot*. The rewrite output is a single string — no inherited claims, no inherited assertions.

The 2026 community consensus, summarized:

- Brute-force full-history hurts via "Lost in the Middle" / attention degradation.
- Naive blind always-rewriting introduces noise.
- **Selective rewriting (only when there is history to resolve against) outperforms both.**

Sources:
- [Multi-turn RAG for Technical Documentation (HF Forums, 2026)](https://discuss.huggingface.co/t/multi-turn-rag-for-technical-documentation-using-context-aware-query-rewriting-semantic-caching-is-this-a-sound-approach/172433) — defines "context-aware query rewriting" as the lightweight LLM-powered layer whose sole job is to rewrite the user's question into a self-contained query.
- [Query Rewrite in RAG Systems (DEV.to, 2026)](https://dev.to/yaruyng/query-rewrite-in-rag-systems-why-it-matters-and-how-it-works-3mmd) — *"blindly rewriting every query introduces noise"* (the "selective" part of the consensus).

### What we chose

**Pattern 3, selective.** Implementation:

```text
if history:
    rewritten = rewrite_question(user_message, history)  # one cheap LLM call
    agent_loop(rewritten)
else:
    agent_loop(user_message)                              # turn 1: no rewrite
```

- **Skipped on empty history** — turn 1 has nothing to resolve against; identity-passthrough.
- **Always-on when history is non-empty** — we rewrite *every* turn 2+ rather than try to detect "does this need rewriting?". That detection is itself an LLM judgment call and would add complexity for a small saving.
- **Reasoning effort `minimal`, max output tokens 200** — the rewrite is a tiny task, must be cheap.
- **Output is a single string** in a `{"rewritten_question": "..."}` JSON envelope, structured-output-validated.

The rewrite stage is the **conversation-memory quarantine**: it is the only place in the system that *can* see prior assistant text, and its single output is a question. Whatever the assistant said in the past does not flow into the grounded retrieval path. A test (`test_multi_turn_no_assistant_text_in_loop`) pins this invariant down by inspecting the messages passed to `llm.generate()` inside the agent loop and asserting no `role=assistant` content from prior turns appears.

---

## Loop pattern — schema attached every turn (Pattern A)

The OpenAI structured-output API supports two clean shapes for tool-using agents:

- **Pattern A — schema every turn.** Each `llm.generate(messages, tools=TOOLS, schema=AGENT_OUTPUT_SCHEMA)` call advertises both. The model returns either `tool_calls` or `parsed` per turn, never both at once with the OpenAI adapter.
- **Pattern C — two-phase.** Gathering turns advertise tools only; once the orchestrator decides "enough evidence", a final turn drops tools and forces structured output.

We chose Pattern A. Reasons:

1. Simpler control flow — one shape per iteration, branched on response type (tool_calls vs parsed).
2. Matches the OpenAI Python SDK's modern guidance for combined tools + structured output.
3. The lower-bound rule (≥ 1 search before any AnswerOutput) is enforced by the orchestrator regardless of pattern; Pattern A doesn't lose anything there.
4. The forced-final turn (when budget is exhausted) is a *single special case* — drop tools, attach schema — rather than a permanent regime change. Simpler to reason about.

Source:
- [openai-python — `client.chat.completions.parse` + auto-parse helpers](https://github.com/openai/openai-python/blob/main/helpers.md)

---

## Output schema — flat-with-nullables, hand-written

OpenAI strict mode does **not** support `oneOf`; only `anyOf`. Pydantic v2 with `Field(discriminator="kind")` emits `oneOf` by default. To stay compatible with strict mode without losing the discriminated-union ergonomics inside Python, we ship two artifacts:

1. **A hand-written JSON schema** (`AGENT_OUTPUT_JSON_SCHEMA` in `app/agent/schemas.py`) — a flat object with all 8 fields (`kind`, `answer`, `citations`, `general_knowledge_used`, `general_knowledge_section`, `out_of_scope`, `question`, `options`), every field nullable, every field in `required`, `additionalProperties: false`. Strict-mode-compliant by construction.
2. **A Pydantic discriminated union** (`AnswerOutput | ClarifyingQuestionOutput`) — for type-safe validation in Python after the model returns. Each branch uses `model_config = ConfigDict(extra="ignore")` so Pydantic silently drops the other branch's null fields when narrowing.

This pattern matches the project's tool-schema convention (`app/tools/registry.py` hand-writes JSON schemas for the same reason). The B5 decisions doc anticipated this option: *"The agent's output schema in B8 may be Pydantic-derived — that's a separate decision and does not retroactively change tool inputs."* We chose hand-written.

---

## Loop bounds — what's enforced and how

| Bound | Default | `.env` key | Mechanism |
|---|---|---|---|
| Max tool calls per question | 5 | `AGENT_MAX_TOOL_CALLS` | Strict cap. A batch that would push *executed count* past the limit is rejected entirely before execution; `budget_exhausted` flag flips, next iteration drops tools and forces structured output. |
| Min tool calls before AnswerOutput | 1 (must include `search_convictions`) | hardcoded — invariant | An AnswerOutput emitted with `search_count == 0` is rejected; the orchestrator appends a system reminder and continues. ClarifyingQuestionOutput is exempt. |
| Loop safety bound | 12 iterations | `AGENT_MAX_ITERATIONS` | Catches pathological cycles (model alternates between rejected pre-search answers indefinitely). Raises `AgentError`. |
| Reasoning effort (loop) | `low` | `AGENT_REASONING_EFFORT` | Per `docs/MODEL_CONFIG.md` — tool selection is schema-constrained, deep reasoning is wasteful. |
| Reasoning effort (rewrite) | `minimal` | `REWRITE_REASONING_EFFORT` | Rewrite is a tiny referent-resolution task. |
| `temperature` | omitted | n/a | gpt-5 rejects explicit `temperature=0`. Determinism is enforced by the verifier (B8) and the schema, not by sampling. |
| Max output tokens (loop) | 4096 | `AGENT_MAX_OUTPUT_TOKENS` | Headroom for citations + grounded answer text. |
| Max output tokens (rewrite) | 200 | `REWRITE_MAX_OUTPUT_TOKENS` | The output is one question. |

All env-driven values flow through `app/config/settings.py`; `app/agent/loop.py` and `app/agent/rewrite.py` read `settings.X` at call time so a `.env` change takes effect without code edits.

The upper-bound rejection is **pre-execution**: if the model emits a parallel batch where some calls would push count past 5, *all* calls in that batch are dropped (we don't partially execute). This keeps the per-batch parallel-tool-call semantics simple — either the whole batch runs or none of it does — and the test fixture (`over_budget.yaml`) exercises exactly this path.

---

## Step records — what the orchestrator emits for B9

Per-call audit-log preparation. The agent emits a `StepRecord` per LLM call and per tool call:

```python
StepRecord(
    step_id: str,                  # UUIDv4 generated at emit time
    kind: "llm_call" | "tool_call",
    timestamp: datetime,           # UTC
    payload: dict,                 # request/response or args/result
    usage: TokenUsage | None,      # llm_call only
    tool_name: str | None,         # tool_call only
)
```

USD cost is *not* stored on the record — `app/services/cost.py` derives it from `usage` at audit-log read time, so price corrections re-price old rows retroactively (per the architectural rule from B4).

B9 wraps the result with `question_id` / `conversation_id` and persists each step into `audit_log`. The agent itself doesn't write to the DB.

The first emitted step on a multi-turn turn is the rewrite-stage `StepRecord` (`payload.stage == "rewrite"`); subsequent steps come from the agent loop (`payload.stage == "agent_loop"`).

---

## Tool dispatch — JSON-stringified results, domain-error feedback

Tool results are serialized to JSON strings before being attached to the next LLM turn:

- Pydantic models → `model.model_dump_json()`.
- Lists of Pydantic models → `json.dumps([m.model_dump(mode="json") for m in xs])`.
- Bad arguments (TypeError) → `{"error": "Tool X called with bad arguments: ..."}`.
- Unknown tool name → `{"error": "Tool X does not exist. Available: ..."}` and consumes one of the 5 budget slots.
- `DomainError` (e.g. `PassageNotFoundError`, `EmptyQueryError`) → `{"error": "PassageNotFoundError: passage not found: 'foo'"}` — the model sees the typed error name and adjusts on the next turn (asserted in `test_domain_error_surfaces_to_model`).
- Non-domain exceptions propagate (programming errors, not user-recoverable conditions).

Tool execution is **parallel** (`asyncio.gather`) — when the model emits a batch of tool calls in one response, all execute concurrently. The 5-call budget counts every call regardless of parallelism.

---

## System prompt — git-tracked markdown

`app/agent/prompts/system.md` and `app/agent/prompts/rewrite.md` are git-tracked markdown loaded once at module import via `Path.read_text()`. Not Python f-strings.

Why markdown: the prompts encode policy (Rules A and B verbatim from `CLAUDE.md`, language mirroring, citation contract, undated-conflict guidance) that must survive a code review. Reviewers can scan a markdown file in seconds; spotting a regression in a 60-line Python f-string is harder.

The system prompt's **Rule B undated clause** is the direct consequence of B2's finding that ~13/30 docs are dateless — the model is told explicitly: *"If `document_updated` is missing for one or both conflicting passages, say so — never silently pick the dated one as 'newer'."* A fixture-driven test (`test_undated_conflict_says_undated`) exercises this path.

---

## What B7 deliberately did NOT do

- **Verifier integration** — moves to B8. The agent emits structured output; substring-grounding is the next step.
- **HTTP endpoint** — moves to B9.
- **Audit-log persistence** — moves to B9. B7 emits `StepRecord`s; B9 wraps with `question_id` / `conversation_id` and writes them.
- **Language detection (`app/agent/language.py`)** — moves to B9. The agent's *language mirroring* is a system-prompt instruction; explicit language detection is needed at the HTTP boundary for the deterministic disclaimer, not inside the loop.
- ~~Settings keys for loop bounds — kept as module-level constants in `app/agent/loop.py`.~~ **Reverted in B7.1:** all six tuning values (`agent_max_tool_calls`, `agent_max_iterations`, `agent_max_output_tokens`, `agent_reasoning_effort`, `rewrite_max_output_tokens`, `rewrite_reasoning_effort`) live on `Settings` and are read from `.env` at call time. They're operational knobs (cost control, eval experimentation) — the previous "no abstraction layers for hypothetical future" framing didn't apply because the feature already shipped behind `pydantic-settings`, so adding fields was zero-cost surface area, not a new abstraction. Documented in `.env.example`.
- **OpenAI Agents SDK / pydantic-function-tool helpers** — would violate the single-LLM-point rule. The provider abstraction stays; tool schemas remain hand-written; agent output schema is hand-written.

---

## Files touched in B7

**Created:**
- `app/agent/__init__.py`, `app/agent/loop.py`, `app/agent/rewrite.py`, `app/agent/schemas.py`
- `app/agent/prompts/system.md`, `app/agent/prompts/rewrite.md`
- `tests/agent/__init__.py`, `tests/agent/test_loop_with_stub.py`, `tests/agent/test_rewrite.py`
- `tests/fixtures/agent_scenarios/*.yaml` — `basic_search`, `over_budget`, `pre_search_answer`, `clarifying`, `dated_conflict`, `undated_conflict`, `rewrite_pt`, `multi_turn_with_rewrite`, `tool_error_feedback`
- `scripts/demo_agent.py`
- `docs/b7-decisions.md`

**Edited:**
- `app/errors.py` — added `AgentError` (subclass of `DomainError`)
- `app/main.py` — registered `AgentError` exception handler (HTTP 500)
- `docs/ROADMAP.md` — swapped B7 / B8 contents; added the swap rationale to B8's "Deviations from the original step description"
