"""Tests for app/providers/factory.py — provider selection by config."""

import pytest

from app.config import settings
from app.providers.base import ProviderError
from app.providers.factory import get_llm_provider
from app.providers.openai import OpenAILLM


@pytest.fixture
def configure_openai():
    """Snapshot settings, pre-set a working OpenAI config, restore after."""
    snapshot = (
        settings.llm_provider,
        settings.openai_api_key,
        settings.openai_model,
        settings.openai_timeout_seconds,
    )
    settings.llm_provider = "openai"
    settings.openai_api_key = "sk-test"
    settings.openai_model = "gpt-5.5"
    yield
    (
        settings.llm_provider,
        settings.openai_api_key,
        settings.openai_model,
        settings.openai_timeout_seconds,
    ) = snapshot


def test_factory_returns_openai_llm_with_configured_timeout(configure_openai):
    settings.openai_timeout_seconds = 42.0
    llm = get_llm_provider()
    assert isinstance(llm, OpenAILLM)
    assert llm._client.timeout == 42.0


def test_factory_raises_when_openai_key_missing(configure_openai):
    settings.openai_api_key = None
    with pytest.raises(ProviderError, match="OPENAI_API_KEY"):
        get_llm_provider()


def test_factory_anthropic_not_yet_implemented(configure_openai):
    settings.llm_provider = "anthropic"
    with pytest.raises(ProviderError, match="anthropic"):
        get_llm_provider()


@pytest.mark.parametrize(
    "model",
    [
        "gpt-5.5",
        "gpt-5.5-mini",
        "gpt-5.4",
        "gpt-5.4-mini",
        "gpt-5.4-nano",
        "gpt-5-mini",
        "o4-mini",
        "gpt-5.5-mini-2025-11-15",  # date-suffixed variants must keep working
    ],
)
def test_factory_accepts_allowlisted_models(configure_openai, model: str):
    settings.openai_model = model
    assert isinstance(get_llm_provider(), OpenAILLM)


@pytest.mark.parametrize(
    "model",
    [
        "gpt-5",  # base gpt-5 excluded — only gpt-5-mini is allowed
        "gpt-5-nano",
        "gpt-5.1",  # 5.1 family not in allowlist
        "o3-mini",  # o-series limited to o4-mini
        "gpt-4o",
        "",
        "made-up-model",
    ],
)
def test_factory_rejects_unsupported_models(configure_openai, model: str):
    settings.openai_model = model
    with pytest.raises(ProviderError, match="unsupported OPENAI_MODEL"):
        get_llm_provider()
