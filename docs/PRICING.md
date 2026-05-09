# Pricing — how we keep up-to-date prices without LiteLLM

The provider layer (`app/providers/openai.py`) calls the OpenAI SDK directly. Per-call USD cost is derived in `app/services/cost.py` from a vendored JSON file: `app/providers/_model_prices.json`. This file is a trimmed-down copy of LiteLLM's [`model_prices_and_context_window.json`](https://github.com/BerriAI/litellm/blob/main/model_prices_and_context_window.json) — the de-facto industry source for LLM pricing data.

We refresh the file via `scripts/refresh_prices.py`. A price update is one commit on `_model_prices.json`, visible in `git log`.

## Why not LiteLLM-the-package

LiteLLM ships a unified call layer plus its own pricing dict. We tried that briefly and removed it because:

- The 100+ provider abstraction LiteLLM provides is overkill for two providers (OpenAI in B4, Anthropic in B10) — our own `LLMProvider` protocol already gives us portability at the granularity we need.
- LiteLLM pulls a heavy transitive-dependency tree (tiktoken, jinja2, jsonschema, importlib-metadata, …) for features we don't use (caching, proxy server, callbacks, fallback chains).
- LiteLLM moves fast — frequent releases, occasional breaking changes. Pinning to a specific version then upgrading periodically is more friction than it's worth at this scale.
- The only piece of LiteLLM we actually wanted was the pricing dict. Vendoring the JSON file gives us that with zero runtime dependencies.

## Why not `tokencost`

[`tokencost`](https://github.com/AgentOps-AI/tokencost) is a small library by AgentOps that wraps the same LiteLLM JSON. It would have given us up-to-date prices via `pip upgrade`. Three reasons we still chose vendoring:

1. **Explicit beats implicit.** A reviewer reading `app/providers/_model_prices.json` sees exactly which prices we're using. With `tokencost`, prices are buried inside a transitive dependency.
2. **Zero new deps.** Vendoring gets us to the same data without adding any package.
3. **No external maintenance dependency.** `tokencost` could pause maintenance; the upstream LiteLLM JSON file is much more likely to keep updating because LiteLLM itself depends on it.

If `_model_prices.json` becomes painful (e.g. we expand to dozens of models), `tokencost` is the obvious next step — same data, less file maintenance.

## What's in `_model_prices.json`

The four models the project uses, each with the fields `cost.py` reads:

| Model | Mode | Input $/tok | Output $/tok | Cached $/tok |
|---|---|---|---|---|
| `gpt-5` | chat | 1.25e-06 | 1.0e-05 | 1.25e-07 |
| `gpt-5-mini` | chat | 2.5e-07 | 2.0e-06 | 2.5e-08 |
| `text-embedding-3-large` | embedding | 1.3e-07 | 0.0 | — |
| `text-embedding-3-small` | embedding | 2.0e-08 | 0.0 | — |

Prices are per token, not per million. Multiply token counts directly.

The full upstream entry has more fields (context windows, capabilities, batch pricing, flex/priority tiers); `scripts/refresh_prices.py` filters down via the `KEEP_FIELDS` set so the vendored file stays readable.

## How `cost.py` uses the data

```python
def compute_call_cost_usd(usage: TokenUsage) -> float:
    entry = _prices()[usage.model]
    fresh = usage.prompt_tokens - usage.cached_tokens
    cached_rate = entry.get("cache_read_input_token_cost", entry["input_cost_per_token"])
    return round(
        fresh * entry["input_cost_per_token"]
        + usage.cached_tokens * cached_rate
        + usage.completion_tokens * entry["output_cost_per_token"],
        8,
    )
```

`_prices()` is `lru_cache`-d, so the JSON parses once per process. Tests call `_prices.cache_clear()` to reset between runs.

Adapters return `TokenUsage` only — no USD. The audit log stores tokens. Cost is computed at audit-log read time, which means **a price correction re-prices old rows retroactively**. That's the property the original hand-rolled `pricing.py` couldn't give us.

## Refresh workflow

```bash
uv run python scripts/refresh_prices.py
git diff app/providers/_model_prices.json
# review the diff — these are real money numbers
git add app/providers/_model_prices.json
git commit -m "refresh model prices from upstream"
```

When to refresh:
- Before any release / interview demo (so you're showing current numbers)
- When OpenAI announces a price change (or you read about one)
- On a monthly cron if you want it automated (not wired up — see "Production level-ups" below)

When **not** to refresh:
- During an open eval run — price drift mid-eval would muddy cost comparisons. Lock prices for the duration of the eval and refresh after.

## Adding a new model

1. Add the model identifier to `WANTED_MODELS` in `scripts/refresh_prices.py`.
2. Run the script.
3. The new model now has an entry in `_model_prices.json`.
4. Set `settings.openai_model = "<new-model>"` (or whatever provider field) and tests will pick it up.

If the new model has fields `cost.py` doesn't currently read (e.g. a new `cache_write_input_token_cost` tier), update `KEEP_FIELDS` and `cost.py` together.

## What can go wrong

- **Upstream removes a model.** The script exits non-zero with `MISSING upstream: ['model-id']`. Hopefully you'd notice during the eyeballing-the-diff step.
- **Upstream changes a field name.** `cost.py` raises `KeyError` at the next call; tests catch it on the next CI run since the smoke test loads the real file.
- **You forget to refresh and report stale numbers.** Mitigation: the test suite includes a smoke test that the file parses, but not that it's recent. We could add a freshness assertion (file mtime > 30 days ago) — not currently wired up; documented as a level-up below.

## Production level-ups (not built)

- **CI freshness check.** A weekly GitHub Action runs `refresh_prices.py` and opens a PR if the file changed. Repo owner reviews.
- **Drift assertion in tests.** Test fails if `_model_prices.json` is older than N days, forcing a manual refresh during release prep.
- **Switch to `tokencost`.** If we expand to many models or want auto-refresh-on-pip-upgrade. The cost service interface stays identical — just swap the data source inside `_prices()`.
- **Move pricing to a config service.** For multi-tenant deployments where customers see different rates (markups for managed-service models). Out of scope for the demo.

## References

- [LiteLLM upstream pricing JSON](https://github.com/BerriAI/litellm/blob/main/model_prices_and_context_window.json) — single source of truth used by both LiteLLM and tokencost
- [`tokencost`](https://github.com/AgentOps-AI/tokencost) — the alternative we'd reach for if vendoring becomes painful
- OpenAI pricing page (always reconfirm critical numbers here): <https://openai.com/api/pricing/>
