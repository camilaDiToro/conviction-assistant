# Pricing

Per-call USD cost is derived in `app/services/cost.py` from a vendored JSON file: `app/providers/_model_prices.json`. This file is a trimmed copy of LiteLLM's [`model_prices_and_context_window.json`](https://github.com/BerriAI/litellm/blob/main/model_prices_and_context_window.json) — the de-facto industry source for LLM pricing data.

This setup is intentionally minimal: it's scoped to the challenge. Production deployments would swap in `tokencost`, a config service, or a CI freshness check.

## What's in `_model_prices.json`

The four models the project uses, each with the fields `cost.py` reads:

| Model | Mode | Input $/tok | Output $/tok | Cached $/tok |
|---|---|---|---|---|
| `gpt-5` | chat | 1.25e-06 | 1.0e-05 | 1.25e-07 |
| `gpt-5-mini` | chat | 2.5e-07 | 2.0e-06 | 2.5e-08 |
| `text-embedding-3-large` | embedding | 1.3e-07 | 0.0 | — |
| `text-embedding-3-small` | embedding | 2.0e-08 | 0.0 | — |

Prices are per token, not per million. Multiply token counts directly.

`scripts/refresh_prices.py` filters the upstream entries via `KEEP_FIELDS` so the vendored file stays readable.

## Refresh workflow

```bash
uv run python scripts/refresh_prices.py
git diff app/providers/_model_prices.json
# review the diff — these are real money numbers
git add app/providers/_model_prices.json
git commit -m "refresh model prices from upstream"
```

When to refresh:
- Before any release / interview demo (so you're showing current numbers).
- When OpenAI announces a price change.

When **not** to refresh:
- During an open eval run — price drift mid-eval would muddy cost comparisons. Lock prices for the duration of the eval and refresh after.

## Adding a new model

1. Add the model identifier to `WANTED_MODELS` in `scripts/refresh_prices.py`.
2. Run the script.
3. Set `settings.openai_model = "<new-model>"` (or whatever provider field).

If the new model has fields `cost.py` doesn't currently read (e.g. a new `cache_write_input_token_cost` tier), update `KEEP_FIELDS` and `cost.py` together.

## References

- [LiteLLM upstream pricing JSON](https://github.com/BerriAI/litellm/blob/main/model_prices_and_context_window.json)
- OpenAI pricing page: <https://openai.com/api/pricing/>
