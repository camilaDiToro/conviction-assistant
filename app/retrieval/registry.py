"""Retrieval strategy registry.

A new retrieval strategy registers itself via the ``@register('name')``
decorator at module import. :func:`get_retriever` looks up the chosen
strategy by name (typically from ``settings.retrieval_strategy``).
"""

from collections.abc import Callable

from app.retrieval.base import Retriever

RETRIEVERS: dict[str, Callable[[], Retriever]] = {}


def register(name: str) -> Callable[[Callable[[], Retriever]], Callable[[], Retriever]]:
    """Register a Retriever factory under ``name``. Used at module import."""

    def decorator(factory: Callable[[], Retriever]) -> Callable[[], Retriever]:
        if name in RETRIEVERS:
            raise ValueError(f"retriever {name!r} already registered")
        RETRIEVERS[name] = factory
        return factory

    return decorator


def get_retriever(name: str) -> Retriever:
    """Instantiate the registered retriever named ``name``."""
    if name not in RETRIEVERS:
        available = ", ".join(sorted(RETRIEVERS)) or "<none>"
        raise ValueError(f"unknown retriever {name!r}; available: {available}")
    return RETRIEVERS[name]()


__all__ = ["RETRIEVERS", "get_retriever", "register"]
