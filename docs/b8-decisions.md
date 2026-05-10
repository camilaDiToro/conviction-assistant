# B8 — Decisions log

Per-decision notes for the citation verifier + retry-once-with-feedback retrofit. The roadmap (`docs/ROADMAP.md` § B8) is the contract; this file captures the choices that don't rise to architecture but should be visible to a reviewer.

## Why `app/verifier/` is its own layer (not under `app/services/`)

`app/services/` is the orchestration layer — business logic that composes the data and provider layers under it. The verifier is *neither* orchestration *nor* data access: it's a **policy module**. It owns one normalization specification and one substring check, and it's pure-functional. Putting it under `app/services/` would buy nothing and would risk scope drift (services tend to grow). A standalone `app/verifier/` package signals: this is the deterministic grounding contract; touch the docstring, you've changed the contract.

Layering rule it satisfies: **no SQL, no settings reads, no provider calls**. The agent loop is the only consumer.

## "Strip the offending claim" → drop the failed `Citation` row

The roadmap pins second-failure behavior as: strip the offending claim from the answer; if zero grounded claims remain, fall through to a localized refusal. The interpretation question is what *strip* means. Two viable readings:

1. **Drop the failed `Citation` row only** (chosen). Pure deterministic, no extra LLM call, audit-traceable. The `answer` text the model wrote remains as-is; it loses one of its citations.
2. **Issue a third LLM call to rewrite the answer text without the failed claim.** Honest stripping of the textual claim, but costs an extra call per double-failure and the rewrite can itself fail verification (regress risk).

We chose (1) because it preserves the determinism property (no third LLM call → no third failure mode), keeps cost bounded at exactly two LLM calls per turn, and matches the project's "deterministic-first" character. The trade-off accepted: a sentence in `answer` may still mention something that no longer carries a citation. We accept this — the model had two chances to produce a verbatim quote, and shipping a partial-citation answer is preferable to either refusing or paying for a third call.

If a stronger guarantee is ever needed (e.g. "every sentence in the answer must map to a verified citation"), the level-up is option (2) — gated on its own conversation.

## `VerifiedCitation` provenance is captured at verify time, not lookup time

Each successful verification emits a `VerifiedCitation` carrying `passage_id`, `document_id`, `document_title`, `heading_path`, and the `quote` string. This is surfaced via `AgentResult.verified_citations` so B9's HTTP response can render the enriched citation row directly, without an extra `read_passage` round-trip per citation in the API layer.

The reason this lives in the verifier and not B9 is plumbing pragmatism: the verifier already had to fetch the `Passage` to check the substring. Throwing away that data and re-fetching it in the API layer would duplicate I/O. The verifier is the natural seam.

## No character offsets (yet)

`VerifiedCitation` does NOT carry character-level start/end offsets of the matched span within the passage. Two reasons:

1. **The frontend already has the full passage text** (via `read_passage`) and the `quote` string; it can render highlighted ranges via plain string-find.
2. **Precise offsets are expensive to compute correctly.** The verifier matches on *normalized* text (NBSP collapse, smart-quote folding, em-dash normalization). Mapping a normalized-text offset back to an offset in the original text requires a position-mapping table built during normalization. That's gold-plating for B8.

Level-up path: if F3 needs precise highlight ranges (e.g. for inline highlighting that survives word-wrapping), add a `match_span: tuple[int, int] | None` field on `VerifiedCitation` populated by a position-aware variant of `normalize`. Gated on F3 actually needing it.

## Inline language detector is a B9 seam

The localized-refusal helper in `app/agent/loop.py` uses a tiny PT/ES/EN heuristic (function-word + diacritic markers) over the rewritten question. B9 ships a proper detector at `app/agent/language.py` shared with the disclaimer-language path. The current implementation is a one-line swap when B9 lands — the helper signature stays `_detect_language(text: str) -> str` and the refusal map keys stay `"pt" | "es" | "en"`.

Why not import a language detector library now: scope cap. B8 is the verifier; one-line refusal-language is the only consumer in this step.

## `StepRecord.kind = "verifier"` is the audit-log channel

Widening the `Literal` was the smallest change that lets B9 persist verifier outcomes alongside `llm_call` and `tool_call` rows. The payload shape — `{attempt, all_passed, verified, failures}` — is already JSON-serializable via `model_dump(mode="json")`, so B9's `audit_log` insert path works without further changes.

## Verifier-disabled escape hatch

`settings.verifier_enabled = False` makes the loop skip verification entirely (no step recorded; `AgentResult.verified_citations = None`). This is for tests and operational debugging; the production path always has it `True`. Off-by-default would invert the architectural commitment of this project.

## Test-fixture conftest

`tests/agent/conftest.py` adds an autouse fixture that patches `app.agent.loop.passages_repo.get` to return a passage whose text contains every fixture quote. This was necessary because the B7 tests pre-date the verifier and use `MagicMock` for the session — without the fixture, every B7 test would crash inside the verifier hook trying to `await` on a MagicMock. The fixture is the *minimal* change to keep B7 invariants under verifier semantics; the only B7 test asserting an exact step sequence (`test_basic_search_then_answer`) was updated to include the trailing `"verifier"` step.
