"""Provider factories keyed by ``settings.llm_provider``.

This is the only place production code constructs concrete provider
adapters.
"""

from app.config import settings
from app.providers.base import (
    EmbeddingProvider,
    LLMProvider,
    ProviderError,
)
from app.providers.openai import OpenAIEmbedder, OpenAILLM


def get_llm_provider() -> LLMProvider:
    """Return the configured LLM provider.

    Raises ``ProviderError`` if the configured provider is not yet
    implemented — the caller should treat this as a startup error.
    """
    name = settings.llm_provider
    if name == "openai":
        if not settings.openai_api_key:
            raise ProviderError("LLM_PROVIDER=openai requires OPENAI_API_KEY to be set")
        return OpenAILLM(
            api_key=settings.openai_api_key,
            model=settings.openai_model,
            timeout=settings.openai_timeout_seconds,
        )
    if name == "anthropic":
        raise ProviderError("anthropic adapter lands in ROADMAP B10")
    raise ProviderError(f"unknown LLM provider {name!r}")


def get_embedding_provider() -> EmbeddingProvider:
    """Return the configured embedding provider."""
    name = settings.llm_provider
    if name == "openai":
        if not settings.openai_api_key:
            raise ProviderError("LLM_PROVIDER=openai requires OPENAI_API_KEY to be set")
        return OpenAIEmbedder(
            api_key=settings.openai_api_key,
            model=settings.openai_embedding_model,
            timeout=settings.openai_timeout_seconds,
        )
    if name == "anthropic":
        # No native Anthropic embeddings — production would route to a
        # different provider here (Voyage, OpenAI, local bge-m3). Out of
        # scope until the hybrid-retrieval level-up is taken.
        raise ProviderError("no embedding provider configured for LLM_PROVIDER=anthropic")
    raise ProviderError(f"unknown embedding provider for {name!r}")
