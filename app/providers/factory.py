"""Provider factory keyed by ``settings.llm_provider``.

This is the only place production code constructs concrete provider
adapters.
"""

from app.config import settings
from app.providers.base import LLMProvider, ProviderError
from app.providers.openai import OpenAILLM

_SUPPORTED_MODEL_PREFIXES: tuple[str, ...] = (
    "gpt-5.5",  # gpt-5.5, gpt-5.5-mini (default family)
    "gpt-5.4",  # gpt-5.4, gpt-5.4-mini, gpt-5.4-nano
    "gpt-5-mini",  # previous generation, mature in tool-use
    "o4-mini",  # reasoning-series control
)


def get_llm_provider() -> LLMProvider:
    """Return the configured LLM provider.

    Raises ``ProviderError`` when the provider is not yet implemented or
    when ``OPENAI_MODEL`` is not in the allowlist — the caller should
    treat both as startup errors.
    """
    name = settings.llm_provider
    if name == "openai":
        if not settings.openai_api_key:
            raise ProviderError("LLM_PROVIDER=openai requires OPENAI_API_KEY to be set")
        model = settings.openai_model
        if not _is_supported_model(model):
            raise ProviderError(
                f"unsupported OPENAI_MODEL={model!r}. Supported: "
                "gpt-5.5, gpt-5.5-mini, gpt-5.4, gpt-5.4-mini, gpt-5.4-nano, "
                "gpt-5-mini, o4-mini"
            )
        return OpenAILLM(
            api_key=settings.openai_api_key,
            model=model,
            timeout=settings.openai_timeout_seconds,
        )
    if name == "anthropic":
        raise ProviderError("anthropic adapter is not yet implemented")
    raise ProviderError(f"unknown LLM provider {name!r}")


def _is_supported_model(model: str) -> bool:
    """True when ``model`` starts with one of the allowlisted prefixes."""
    lowered = model.lower()
    return any(lowered.startswith(prefix) for prefix in _SUPPORTED_MODEL_PREFIXES)
