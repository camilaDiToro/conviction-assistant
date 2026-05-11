"""Refresh ``app/providers/_model_prices.json`` from upstream LiteLLM data.

Run::

    uv run python scripts/refresh_prices.py

See ``README.md`` § "Refreshing model prices" for the workflow.

``WANTED_MODELS`` must cover every model the runtime uses — that means
``settings.allowed_models`` (the ``/chat`` override whitelist) plus the
embedding models. When a wanted model is not in upstream (e.g. a
just-announced flagship that LiteLLM hasn't picked up yet), the script
WARNS and preserves the existing manual entry from the vendored JSON;
review those by hand against OpenAI's pricing page.
"""

import json
import sys
import urllib.request
from pathlib import Path

UPSTREAM_URL = (
    "https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json"
)
TARGET = Path(__file__).resolve().parents[1] / "app" / "providers" / "_model_prices.json"
# Must cover settings.allowed_models + the embedding models. Newer
# models (gpt-5.5, gpt-5.4-mini) may not yet exist upstream — the
# script preserves their manual entries when that happens.
WANTED_MODELS = [
    "gpt-5.5",
    "gpt-5.4-mini",
    "gpt-5.1",
    "gpt-5",
    "gpt-5-mini",
    "gpt-4.1",
    "gpt-4o",
    "text-embedding-3-large",
    "text-embedding-3-small",
]
# Fields we keep per model. Anything else upstream gets dropped — keeps
# the vendored JSON readable. Update this list if cost.py starts using
# additional fields. ``_note`` is preserved when present so manual
# annotations on approximate prices survive a refresh.
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
    "_note",
}


def main() -> int:
    print(f"Fetching {UPSTREAM_URL}")
    with urllib.request.urlopen(UPSTREAM_URL, timeout=30) as resp:
        upstream: dict[str, dict] = json.loads(resp.read().decode("utf-8"))

    current: dict[str, dict] = {}
    if TARGET.exists():
        current = json.loads(TARGET.read_text(encoding="utf-8"))

    out: dict[str, dict] = {}
    refreshed: list[str] = []
    preserved: list[str] = []
    missing: list[str] = []
    for model in WANTED_MODELS:
        entry = upstream.get(model)
        if entry is not None:
            out[model] = {k: v for k, v in entry.items() if k in KEEP_FIELDS}
            refreshed.append(model)
        elif model in current:
            out[model] = current[model]
            preserved.append(model)
        else:
            missing.append(model)

    if preserved:
        print(
            f"WARNING: not in upstream — preserved existing entries: {preserved}",
            file=sys.stderr,
        )
    if missing:
        print(
            f"ERROR: not in upstream and no existing entry: {missing}. "
            f"Add a manual entry or remove from WANTED_MODELS.",
            file=sys.stderr,
        )
        return 1

    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        f"Wrote {TARGET} "
        f"({len(refreshed)} refreshed, {len(preserved)} preserved)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
