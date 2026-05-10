"""FastAPI dependencies for the API layer.

Currently exposes :func:`get_llm_provider_dep`, which the /chat handler
depends on. Tests override this via ``app.dependency_overrides`` to
inject a :class:`StubLLM` and never burn provider tokens in CI.
"""

from app.providers import LLMProvider, get_llm_provider


def get_llm_provider_dep() -> LLMProvider:
    """Return the configured LLM provider for the current request.

    Production: delegates to :func:`app.providers.get_llm_provider`.
    Tests: overridden via ``app.dependency_overrides``.
    """
    return get_llm_provider()


__all__ = ["get_llm_provider_dep"]
