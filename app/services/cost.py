"""USD cost computation for one provider call.

This is a pure function over ``TokenUsage`` and is the *only* place USD
prices enter the project. Adapters in ``app/providers/`` return token
counts; the audit log records token counts; cost-in-USD is derived here
when an audit-log row is read.

Pricing data
------------

Prices come from ``app/providers/_model_prices.json``, which is a
trimmed copy of LiteLLM's ``model_prices_and_context_window.json``
(the de-facto industry source — see ``docs/PRICING.md``). Prices are
**per token** (not per million); we multiply token counts directly.
"""

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.providers.base import ProviderError, TokenUsage

_PRICES_PATH = Path(__file__).resolve().parents[1] / "providers" / "_model_prices.json"


@lru_cache(maxsize=1)
def _prices() -> dict[str, dict[str, Any]]:
    """Load and cache the vendored pricing table.

    ``lru_cache`` caches the parsed JSON for the life of the process;
    tests that need fresh data (e.g. after monkey-patching the file)
    call ``_prices.cache_clear()``.
    """
    return json.loads(_PRICES_PATH.read_text(encoding="utf-8"))


def compute_call_cost_usd(usage: TokenUsage) -> float:
    """Compute USD cost for one ``TokenUsage`` row.

    Splits ``cached_tokens`` into the cached-input tier (priced at
    ``cache_read_input_token_cost`` when the model supports caching;
    otherwise at the regular input price) and the remainder into the
    fresh-input tier. Raises ``ProviderError`` for unknown models so a
    missing pricing entry is loud, not silently $0.
    """
    if usage.cached_tokens > usage.prompt_tokens:
        raise ProviderError(
            f"cached_tokens ({usage.cached_tokens}) exceeds prompt_tokens ({usage.prompt_tokens})"
        )
    entry = _prices().get(usage.model)
    if entry is None:
        raise ProviderError(f"no pricing entry for model {usage.model!r}")

    input_cost = entry["input_cost_per_token"]
    output_cost = entry["output_cost_per_token"]
    cached_cost = entry.get("cache_read_input_token_cost", input_cost)

    fresh_input = usage.prompt_tokens - usage.cached_tokens
    cost = (
        fresh_input * input_cost
        + usage.cached_tokens * cached_cost
        + usage.completion_tokens * output_cost
    )
    return round(cost, 8)
