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
from app.providers.openai import OpenAIEmbedder, OpenAILLM, OpenAIResponsesLLM


def get_llm_provider(model: str | None = None) -> LLMProvider:
    """Return the configured LLM provider.

    ``model`` is an optional per-call override. When ``None`` the
    provider is bound to ``settings.openai_model``. Used by the /chat
    handler to honour per-request model overrides without rebinding the
    process-wide default.

    Raises ``ProviderError`` if the configured provider is not yet
    implemented — the caller should treat this as a startup error.
    """
    name = settings.llm_provider
    if name == "openai":
        if not settings.openai_api_key:
            raise ProviderError("LLM_PROVIDER=openai requires OPENAI_API_KEY to be set")
        chosen_model = model or settings.openai_model
        cls = OpenAIResponsesLLM if _requires_responses_api(chosen_model) else OpenAILLM
        return cls(
            api_key=settings.openai_api_key,
            model=chosen_model,
            timeout=settings.openai_timeout_seconds,
        )
    if name == "anthropic":
        raise ProviderError("anthropic adapter is not yet implemented")
    raise ProviderError(f"unknown LLM provider {name!r}")


def _requires_responses_api(model: str) -> bool:
    """gpt-5.4 and gpt-5.5 reject function tools + reasoning_effort on
    /v1/chat/completions and demand /v1/responses. gpt-5.1, gpt-5,
    gpt-5-mini, and all non-reasoning chat models still work on chat
    completions."""
    name = model.lower()
    return name.startswith(("gpt-5.4", "gpt-5.5", "gpt-5.6", "gpt-5.7"))


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
