"""Refresh ``app/providers/_model_prices.json`` from upstream LiteLLM data.

Run::

    uv run python scripts/refresh_prices.py

The script downloads LiteLLM's
``model_prices_and_context_window.json`` (the industry-standard source
for LLM pricing data — see ``docs/PRICING.md``), filters down to the
models this project uses, and overwrites the local pricing table.

Review the diff with ``git diff app/providers/_model_prices.json``
before committing — a price change should be a small, reviewable
commit, not a silent dependency upgrade.

Why we don't add upstream as a runtime dependency: the LiteLLM Python
package ships a large abstraction layer + dozens of transitive deps we
don't need. The pricing JSON is the only piece we use, so we vendor it.

To add a new model: append its identifier to ``WANTED_MODELS`` below
and re-run the script.
"""

from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

UPSTREAM_URL = (
    "https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json"
)
TARGET = Path(__file__).resolve().parents[1] / "app" / "providers" / "_model_prices.json"
WANTED_MODELS = [
    "gpt-5",
    "gpt-5-mini",
    "text-embedding-3-large",
    "text-embedding-3-small",
]
# Fields we keep per model. Anything else upstream gets dropped — keeps
# the vendored JSON readable. Update this list if cost.py starts using
# additional fields.
KEEP_FIELDS = {
    "input_cost_per_token",
    "output_cost_per_token",
    "cache_read_input_token_cost",
    "litellm_provider",
    "max_input_tokens",
    "max_output_tokens",
    "max_tokens",
    "mode",
    "output_vector_size",
    "supports_prompt_caching",
    "supports_response_schema",
}


def main() -> int:
    print(f"Fetching {UPSTREAM_URL}")
    with urllib.request.urlopen(UPSTREAM_URL, timeout=30) as resp:
        upstream: dict[str, dict] = json.loads(resp.read().decode("utf-8"))

    out: dict[str, dict] = {}
    missing: list[str] = []
    for model in WANTED_MODELS:
        entry = upstream.get(model)
        if entry is None:
            missing.append(model)
            continue
        out[model] = {k: v for k, v in entry.items() if k in KEEP_FIELDS}

    if missing:
        print(
            f"ERROR: model(s) not found upstream: {missing}",
            file=sys.stderr,
        )
        return 1

    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote {TARGET} ({len(out)} models, {len(KEEP_FIELDS)} fields each)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
