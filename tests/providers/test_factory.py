"""Tests for app/providers/factory.py — provider selection by config."""

import pytest

from app.config import settings
from app.providers.base import ProviderError
from app.providers.factory import get_embedding_provider, get_llm_provider
from app.providers.openai import OpenAIEmbedder, OpenAILLM


@pytest.fixture
def reset_settings():
    """Snapshot/restore the bits of `settings` we mutate per test."""
    snapshot = (
        settings.llm_provider,
        settings.openai_api_key,
        settings.openai_model,
        settings.openai_embedding_model,
        settings.openai_timeout_seconds,
    )
    yield
    (
        settings.llm_provider,
        settings.openai_api_key,
        settings.openai_model,
        settings.openai_embedding_model,
        settings.openai_timeout_seconds,
    ) = snapshot


def test_factory_returns_openai_llm_when_configured(reset_settings):
    settings.llm_provider = "openai"
    settings.openai_api_key = "sk-test"
    settings.openai_model = "gpt-5"
    provider = get_llm_provider()
    assert isinstance(provider, OpenAILLM)


def test_factory_returns_openai_embedder_when_configured(reset_settings):
    settings.llm_provider = "openai"
    settings.openai_api_key = "sk-test"
    settings.openai_embedding_model = "text-embedding-3-large"
    embedder = get_embedding_provider()
    assert isinstance(embedder, OpenAIEmbedder)


def test_factory_raises_when_openai_key_missing(reset_settings):
    settings.llm_provider = "openai"
    settings.openai_api_key = None
    with pytest.raises(ProviderError, match="OPENAI_API_KEY"):
        get_llm_provider()
    with pytest.raises(ProviderError, match="OPENAI_API_KEY"):
        get_embedding_provider()


def test_factory_anthropic_not_yet_implemented(reset_settings):
    settings.llm_provider = "anthropic"
    with pytest.raises(ProviderError, match="B10"):
        get_llm_provider()


def test_factory_passes_timeout_from_settings(reset_settings):
    settings.llm_provider = "openai"
    settings.openai_api_key = "sk-test"
    settings.openai_timeout_seconds = 42.0
    llm = get_llm_provider()
    embedder = get_embedding_provider()
    assert isinstance(llm, OpenAILLM)
    assert isinstance(embedder, OpenAIEmbedder)
    assert llm._client.timeout == 42.0
    assert embedder._client.timeout == 42.0
