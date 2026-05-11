"""Retrieval strategy registry.

Each strategy is a factory listed explicitly in `_RETRIEVERS`. `get_retriever`
returns a fresh instance; `available_retrievers` lists the registered names
(used by the parametrized conformance test).
"""

from collections.abc import Callable

from app.retrieval.base import Retriever
from app.retrieval.bm25 import BM25Retriever

_RETRIEVERS: dict[str, Callable[[], Retriever]] = {
    "bm25": BM25Retriever,
}


def available_retrievers() -> list[str]:
    return sorted(_RETRIEVERS)


def get_retriever(name: str) -> Retriever:
    """Instantiate the registered retriever named ``name``."""
    factory = _RETRIEVERS.get(name)
    if factory is None:
        available = ", ".join(available_retrievers()) or "<none>"
        raise ValueError(f"unknown retriever {name!r}; available: {available}")
    return factory()


__all__ = ["available_retrievers", "get_retriever"]
