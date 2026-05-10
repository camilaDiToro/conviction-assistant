"""Retriever Protocol — the single contract every retrieval strategy implements.

Strategies live under :mod:`app.retrieval` as one file each. New strategies
register via ``@register('name')`` in their module; the chosen strategy
is built once at lifespan via :func:`app.retrieval.get_retriever` and
held on ``app.state.retriever``.

Today's only strategy is :class:`app.retrieval.bm25.BM25Retriever`. The
documented level-up (BM25 + multilingual dense + RRF) drops in as a new
file with a ``@register('hybrid')`` decorator and a widened
``settings.retrieval_strategy`` Literal — no edit to call sites.
"""

from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.passage import Passage


class Retriever(Protocol):
    """The single contract every retrieval strategy implements.

    ``build`` is called once at startup; ``rebuild`` is called after each
    ``POST /admin/ingest``. ``search`` is hot-path (called by the
    ``search_convictions`` tool on every agent turn that retrieves).
    """

    async def build(self, session: AsyncSession) -> None: ...

    async def rebuild(self, session: AsyncSession) -> None: ...

    def search(self, query: str, k: int) -> list[tuple[Passage, float]]: ...


__all__ = ["Retriever"]
