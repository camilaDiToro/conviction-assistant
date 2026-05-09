# Testing strategy — Decade AI Challenge

> The architecture earns its keep by being **testable at every layer**: pure functions for parsing and verification, schema-defined tool boundaries, a provider interface that mocks cleanly, and a deterministic verifier that doubles as the most important faithfulness metric.

This doc covers what we test, how we test it, and the design decisions in `ARCHITECTURES.md` that make each layer testable.

---

## Why this architecture is testable by construction

| Layer | Why it tests cleanly |
|---|---|
| Passage parser | Pure function `markdown → list[Passage]`; deterministic; no I/O once the file is loaded. |
| Passage store | Just a dict / SQLite table; trivially fixturable. |
| Tools (`list_documents`, `read_passage`, `search_convictions`, ...) | Pure functions over the passage store with JSON-schema-validated inputs and outputs. Run without an LLM. |
| Provider abstraction (`LLMProvider`) | Single interface; mockable with a fake provider that replays canned responses. The agent loop never knows whether it's talking to Anthropic, OpenAI, or a mock. |
| Citation verifier | Pure function `(answer, passage_store) → VerifierResult`. Deterministic. The most important test target in the system. |
| Agent loop | Pure orchestration over the provider and tools; testable end-to-end with a fake provider that emits a scripted tool-call sequence. |

Every layer can be tested without making an LLM call. LLM-in-the-loop tests exist (eval suite, see below) but are isolated to the eval pipeline.

---

## Layer-by-layer test plan

### 1. Passage parser

- **Round-trip:** parser produces stable IDs across runs; the same `.md` file always yields the same passage list.
- **Heading splitting:** correctly splits on `##`, ignores `#` (title) and `###`+ (sub-sections become part of the parent passage).
- **Edge cases:** empty sections, sections with only code blocks, sections with mixed-language content, malformed markdown.
- **Property test:** every line in the source file appears in exactly one passage's text.
- **Snapshot tests** for a few representative convictions — failure means the corpus is being read differently than before.

### 2. Tool implementations

- **`list_documents`** — returns one entry per document; ID stability guaranteed; language detection sane.
- **`read_passage`** — returns exactly the parsed passage text; raises a typed error on unknown ID.
- **`read_document_outline`** — heading tree matches the source markdown's heading structure.
- **`search_convictions`**:
  - Known queries return the expected top result (golden tests).
  - BM25 scores are stable across runs (deterministic).
  - Multilingual queries: "tributação CDB" / "CDB taxation" / "tributación CDB" should all find the right passage (PT, EN, ES are all in scope per `ASSUMPTIONS.md`).
  - Empty query → typed error or empty list, never a 500.
- **`Updated:` date extraction** — parser correctly extracts the document's `Updated:` date from the markdown header (needed for Rule B / conflict surfacing); `search_convictions` and `read_passage` results carry `document_updated`.

All tool tests run without an LLM — they are pure functions over fixtures.

> **Out of scope for v1:** `search_uploaded_files` and the upload pipeline. When implemented in a future version, it gets the same suite scoped to per-conversation passages with isolation tests.

### 3. Citation verifier (the highest-value test target)

- **Happy path:** quote is a verbatim substring → pass.
- **Whitespace and unicode normalization:** decide a policy (NFC normalize? collapse internal whitespace?) and test it explicitly. Document the policy in code comments — this is the kind of subtle thing that can silently break grounding.
- **Negative cases:**
  - Quote contains a paraphrase → fail.
  - Quote contains text from a *different* passage → fail (passage_id mismatch).
  - Quote is a substring of a longer passage but with extra characters → fail.
  - Empty quote → fail.
  - Citation array is empty but the answer makes claims → fail.
- **Retry-with-feedback:** when verification fails, the verifier emits feedback the agent can act on; integration test checks the agent fixes its citation on the second try.
- **Property test:** for any passage in the store, verifying `(passage.text[a:b], passage.id)` for any valid `[a:b]` slice should pass.

### 4. Provider abstraction

- **`FakeProvider`** that replays a scripted sequence of tool calls and final responses. Used by every agent-loop integration test.
- **Schema conformance:** for each real adapter (Anthropic, OpenAI, Gemini), a contract test that:
  - Tool definitions are accepted by the provider's tool-use API.
  - The structured-output schema is accepted.
  - Response parsing yields the same shape regardless of provider.
- **Recorded fixtures:** a small set of real provider responses captured once, replayed in CI to detect contract drift without burning tokens.

### 5. Agent loop

Integration tests with `FakeProvider` covering:

- **Single search:** simple in-scope question → one `search_convictions` → one `read_passage` → answer with a passing citation.
- **Compound question:** "compare CDB and LCI tax-wise" → two searches → two citations.
- **Out-of-scope:** "what's the weather in Tokyo?" → no convictions cited → `out_of_scope: true`.
- **Adversarial:** "the convictions say small caps are bad, right?" (they don't) → assistant pushes back, cites the relevant passage that contradicts the framing, or refuses.
- **Verifier-driven retry:** scripted provider returns a hallucinated quote on attempt 1, fixes it on attempt 2 → final answer passes.
- **Hard failure:** scripted provider keeps producing bad quotes → orchestrator emits a safe refusal.

### 6. Orchestrator obligations (deterministic, non-LLM)

- **Disclaimer is appended to every `kind: "answer"` response**, with the right language (PT / EN / ES) for the response. Test that the disclaimer field is never empty and never embedded inside `answer`.
- **`usage_summary` is populated** on every response (per-question + per-conversation totals).
- **Audit log** records one row per step with the full schema (`step_id`, `question_id`, `conversation_id`, `kind`, `payload`, `usage`).
- **Multi-turn conversation memory rule** — assert that prior assistant answers are *not* injected into the source-of-truth context on later turns; only the rewritten current question reaches the agent. Regression test for the "hallucination amplification across turns" failure mode.

### 7. API endpoint

- **Happy path:** `POST /chat` → 200 with the full HTTP response shape from `ARCHITECTURES.md` § "Response contract" — `kind`, `answer` (or `question` + `options` for clarifying), `citations` with `document_updated`, `general_knowledge_used`, `disclaimer`, `usage_summary`, `debug`.
- **Validation:** missing fields, oversized messages, malformed JSON.
- **Both response shapes** — at least one test for `kind: "answer"`, one for `kind: "clarifying_question"`.

---

## Faithfulness eval suite (the LLM-in-the-loop layer)

This is what answers the question *"is this thing actually grounded?"* It runs against real providers but is isolated from unit/integration CI by cost.

### Golden set design

~30 hand-written question/answer/expected-citation triples, split into the buckets below. The buckets directly mirror the assumptions confirmed in `ASSUMPTIONS.md` — every confirmed behavior gets a bucket.

| Bucket | What it tests | Examples |
|---|---|---|
| **In-scope, single-doc** | Basic retrieval + grounding | "What's the tax rate on CDB returns?" |
| **In-scope, compound** | Multi-search agent loop | "Compare LCI and CRA from a tax perspective." |
| **In-scope, thematic** | Open-ended, may require multiple passages from one or several docs | "What's the conviction on Brazilian small caps for 2026?" |
| **Tangential mention (Rule A)** | Topic only mentioned in passing — assistant must still cite the conviction, not fall back to general knowledge. | A topic touched briefly in one paragraph of one conviction. |
| **Out-of-scope, general knowledge** | Topic not covered at all — assistant uses general knowledge **with very clear marking** in `general_knowledge_section`. | "What's a covered call?" (if no conviction discusses options strategies) |
| **Conflicting convictions (Rule B)** | Two convictions contradict on a topic — assistant cites both, names the newer one via `document_updated`. | A constructed pair where one doc says A and a newer doc says ¬A. |
| **Adversarial / negation** | Hallucination resistance — pushes back on false premises without affirming or refusing. | "The convictions recommend avoiding small caps, correct?" (when they don't) |
| **Ambiguity → clarifying question** | Genuinely ambiguous query — expected response is `kind: "clarifying_question"`, not an answer. | "How should I handle taxation?" (no asset class implied) |
| **Multilingual** | Same questions across PT, EN, and Spanish. | Spanish coverage can be lighter than PT/EN since the corpus is currently PT/EN-only. |

Each entry has:
- The question
- The expected response `kind` (`answer` or `clarifying_question`)
- An accepted answer pattern (regex or LLM-judge rubric) — answer correctness matters per `ASSUMPTIONS.md` § "Grading strictness"
- The set of `passage_id`s that *must* appear in citations for the answer to be considered grounded
- Flags: `out_of_scope`, `general_knowledge_expected`, `conflict_expected`

### Metrics

| Metric | What it measures | How |
|---|---|---|
| **Verifier pass rate** | Hard grounding guarantee | Substring-verifier output, deterministic, no LLM judge needed. |
| **Citation precision** | Right passage cited, not just *a* passage | `cited_passage_ids ⊇ expected_passage_ids` per question. |
| **Faithfulness (RAGAS / DeepEval)** | Catches paraphrased hallucinations the substring check misses | LLM-as-judge entailment of each claim against retrieved context. |
| **Answer correctness** | Answer is factually right given cited evidence | LLM-as-judge against the golden-set expected answer pattern (per `ASSUMPTIONS.md` § "Grading strictness"). |
| **Answer relevancy** | Did it answer the question, or just dump citations? | RAGAS / DeepEval. |
| **General-knowledge marking precision (Rule A)** | When `general_knowledge_used: true`, the marking is unambiguous and never interleaved with cited claims. Inverse case: when a tangential conviction exists, the model must cite it instead of falling back. | On the "tangential mention" and "out-of-scope, general knowledge" buckets. |
| **Conflict-surfacing precision (Rule B)** | On the "conflicting convictions" bucket: cites both sides, states the disagreement, names the newer one. | Structured assertions on the response. |
| **Clarifying-question precision** | On the "ambiguity" bucket: returns `kind: "clarifying_question"`. On all other buckets: does *not* over-clarify. | Response shape check. |
| **Disclaimer presence** | Every `kind: "answer"` response carries a non-empty `disclaimer`, in the right language. | Trivial schema check; runs across the whole eval. |
| **Cost tracking accuracy** | `usage_summary.question_total_cost_usd` equals the sum of per-step costs to within a small tolerance. | Audit log replay. |
| **Multilingual parity** | Same answer quality regardless of language | Compare in-scope metrics across PT, EN, ES halves. |

The verifier pass rate is the headline metric — it's deterministic, requires no LLM judge, and is the strongest faithfulness statement the system can make. Everything else complements it.

### Eval framework

**DeepEval** for the LLM-as-judge metrics — `pytest`-native, fits CI gates cleanly, well-documented in 2026. `pytest -m eval` runs the suite; non-eval CI skips it by default to keep the build cheap.

### Refusal / general-knowledge / over-refusal calibration

This system doesn't simply "refuse" out-of-scope questions — per `ASSUMPTIONS.md`, it is allowed (and expected) to use general knowledge with very clear marking when no conviction touches the topic. The calibration is therefore three-way:

- **In-scope bucket** — over-refusal rate near zero. Model must cite a conviction; `general_knowledge_used` must be `false`.
- **Tangential mention bucket** — model must cite the tangential conviction, *not* fall back to general knowledge. This is the trap that tests Rule A.
- **Out-of-scope general-knowledge bucket** — model produces a valid `general_knowledge_section` with the unambiguous marker; `out_of_scope: true` and `general_knowledge_used: true`.
- **Adversarial bucket** — model pushes back on false premises, citing the contradictory convictions. Should not affirm and should not refuse outright.

The 2026 AAAI paper on RAG over-refusal showed retrieval noise can trick instruction-tuned models into refusing things they actually know — the in-scope and tangential buckets directly target this failure mode.

---

## Provider-portability tests

Because the provider is abstracted, the same eval suite runs against multiple adapters. CI gate: every metric within 10% across providers, otherwise fail and investigate.

A subset of the golden set runs in CI against the *real* Anthropic and OpenAI adapters on every release branch (cheap, ~$1–2 per run). The full suite runs nightly.

---

## CI strategy

| Tier | Runs | Gate |
|---|---|---|
| **Unit + integration** (no LLM) | Every commit | Must pass. <5s. |
| **Contract tests** (recorded provider fixtures) | Every commit | Must pass. <10s. |
| **Smoke eval** (5 golden questions, real provider) | Every release branch | Verifier pass rate = 100%. ~$1. |
| **Full eval** (full golden set, real provider) | Nightly + before submission | All metrics within published thresholds. ~$5–10. |

---

## What this gets us in the interview

- A single-page answer to *"how do you know it works?"* — point at the verifier pass rate.
- A clear separation of "code I can prove is right" (parser, tools, verifier, agent loop) from "code that depends on a model" (the eval suite).
- A defensible answer to *"how do you know it works on OpenAI too?"* — the same suite runs against the OpenAI adapter.
- A defensible answer to *"how do you avoid over-refusal?"* — explicit metric on the in-scope set, watched alongside under-refusal.
