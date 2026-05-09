"""Tests for app/services/cost.py — USD computation from TokenUsage.

Tests stub the vendored pricing table via ``_prices.cache_clear`` +
monkeypatch, so they don't depend on the actual values in
``app/providers/_model_prices.json`` (which change as upstream prices
move). One smoke test confirms the real file parses.
"""

import pytest

from app.providers.base import ProviderError, TokenUsage
from app.services import cost as cost_module
from app.services.cost import _prices, compute_call_cost_usd


def _usage(prompt=0, completion=0, cached=0, model="gpt-5"):
    return TokenUsage(
        model=model,
        prompt_tokens=prompt,
        completion_tokens=completion,
        cached_tokens=cached,
    )


@pytest.fixture
def stub_prices(monkeypatch):
    """Replace the cached price table with a deterministic stub."""
    table = {
        "gpt-5": {
            "input_cost_per_token": 1.25e-06,
            "output_cost_per_token": 1e-05,
            "cache_read_input_token_cost": 1.25e-07,
            "mode": "chat",
        },
        "no-cache-model": {
            "input_cost_per_token": 5e-07,
            "output_cost_per_token": 5e-06,
            "mode": "chat",
        },
        "text-embedding-3-large": {
            "input_cost_per_token": 1.3e-07,
            "output_cost_per_token": 0.0,
            "mode": "embedding",
        },
    }
    _prices.cache_clear()
    monkeypatch.setattr(cost_module, "_prices", lambda: table)
    yield table
    _prices.cache_clear()


def test_compute_call_cost_no_cache(stub_prices):
    usage = _usage(prompt=1000, completion=200)
    expected = 1000 * 1.25e-06 + 200 * 1e-05
    assert compute_call_cost_usd(usage) == pytest.approx(expected)


def test_compute_call_cost_completion_priced_higher(stub_prices):
    cost = compute_call_cost_usd(_usage(prompt=0, completion=1_000_000))
    assert cost == pytest.approx(10.0)  # 1M * 1e-5


def test_compute_call_cost_all_cached_uses_cached_tier(stub_prices):
    cost = compute_call_cost_usd(_usage(prompt=1000, cached=1000))
    assert cost == pytest.approx(1000 * 1.25e-07)


def test_compute_call_cost_partial_cache_splits_tiers(stub_prices):
    # 600 cached + 400 fresh + 100 completion
    cost = compute_call_cost_usd(_usage(prompt=1000, completion=100, cached=600))
    expected = 400 * 1.25e-06 + 600 * 1.25e-07 + 100 * 1e-05
    assert cost == pytest.approx(expected)


def test_compute_call_cost_model_without_cache_falls_back_to_input_price(stub_prices):
    """Models that don't support caching price cached_tokens at the input rate."""
    cost = compute_call_cost_usd(_usage(prompt=1000, cached=400, model="no-cache-model"))
    # All 1000 prompt tokens billed at the regular input price.
    assert cost == pytest.approx(1000 * 5e-07)


def test_compute_call_cost_unknown_model_raises(stub_prices):
    with pytest.raises(ProviderError, match="no pricing entry"):
        compute_call_cost_usd(_usage(prompt=10, model="not-a-real-model"))


def test_compute_call_cost_cached_exceeds_prompt_raises(stub_prices):
    with pytest.raises(ProviderError, match="exceeds prompt_tokens"):
        compute_call_cost_usd(_usage(prompt=10, cached=11))


def test_compute_call_cost_zero_tokens_returns_zero(stub_prices):
    assert compute_call_cost_usd(_usage()) == 0.0


def test_compute_call_cost_does_not_double_bill_reasoning_tokens(stub_prices):
    """reasoning_tokens are inside completion_tokens — must not add a second charge."""
    base = _usage(prompt=100, completion=500)
    with_reasoning = TokenUsage(
        model="gpt-5",
        prompt_tokens=100,
        completion_tokens=500,
        cached_tokens=0,
        reasoning_tokens=400,
    )
    assert compute_call_cost_usd(base) == compute_call_cost_usd(with_reasoning)


def test_vendored_prices_file_parses():
    """Smoke: the actual JSON file in the repo loads and has our models."""
    _prices.cache_clear()
    table = _prices()
    for model in ["gpt-5", "gpt-5-mini", "text-embedding-3-large", "text-embedding-3-small"]:
        assert model in table, f"vendored prices missing {model}"
        assert "input_cost_per_token" in table[model]
        assert "output_cost_per_token" in table[model]
