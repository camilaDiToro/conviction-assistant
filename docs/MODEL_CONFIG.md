# MODEL_CONFIG.md — gpt-5 knob choices

Why each tuning param has the value it does, for *this* use case (constrained agentic loop over 30 conviction docs + deterministic substring verifier).

## Knob → use-case mapping

| Knob | Default | Tool-routing turns | Final-answer turn | Why |
|---|---|---|---|---|
| `temperature` | unset (omitted from API call) | unset | unset | gpt-5 rejects explicit `temperature`. Determinism comes from the verifier rejecting non-grounded citations, not from `temperature=0`. |
| `reasoning_effort` | unset (provider default) | `"low"` | `"low"` | Tool selection is schema-constrained; final synthesis is bounded by retrieval. Neither task is multi-step reasoning. `"medium"` would 2–3× latency and reasoning-token spend without measurable quality gain. |
| `verbosity` | unset | unset | `"low"` | Schema bounds the surface; verbosity controls chattiness *within* fields. Decade analysts want signal. |
| `max_output_tokens` | unset | `~200` | `~800` | Defense in depth. Final answer is bounded by the schema (~400 tok answer + ≤8 citations × ~30 tok). 800 = 2× natural ceiling — generous but fails loud on a runaway. |
| `openai_timeout_seconds` (settings) | `60.0` | — | — | `reasoning_effort=low` calls return in 5–15s; 60s = 4× headroom. Agent loop bounded at 5 turns → worst-case 5min request budget. SDK default is 10min, wrong for an interactive `/chat`. |

The orchestrator (B8) is the only place that picks per-call values. The protocol exposes the params; nothing defaults them.

## `reasoning_tokens` capture

Reported separately on `TokenUsage` but **not double-billed** — OpenAI already counts these inside `completion_tokens`. The cost path stays unchanged. The field is for visibility ("where did the tokens go on this gpt-5 call?").

## What we did NOT do

- **OpenAI Responses API.** Chat completions still works for gpt-5 and is the more portable contract (Anthropic and the rest speak chat completions). gpt-5.4 will force migration; documented as a deferred level-up. The change would be local to `app/providers/openai.py`.
- **Per-model whitelist for `temperature`.** Brittle when new models drop. Adapter just omits unset kwargs; if a caller explicitly passes `temperature=0.7` against gpt-5, the upstream API error is the right failure mode.
- **`strict: true` opt-out on tools.** B5 tool authors are us; we will write strict-compliant schemas. Adding a flag would muddy the cross-provider protocol (Anthropic has no strict mode).

## Anthropic counterpart (B10)

Claude's `extended_thinking` is the analog to `reasoning_effort`; `max_tokens` is the analog to `max_output_tokens`. The Anthropic adapter (B10) translates `reasoning_effort` → `extended_thinking` budget and ignores `verbosity`. No protocol change.
