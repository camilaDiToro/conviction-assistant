"""Retrieval strategies — Protocol + registry.

The single contract is :class:`Retriever`. Today's only registered
strategy is ``bm25``; the documented level-up is hybrid (BM25 + dense
+ RRF). A new strategy = drop a file in, add a ``@register('name')``
decorator, widen ``settings.retrieval_strategy``. No edit to call sites.
"""

from app.retrieval import bm25  # noqa: F401 — import side effect: registers 'bm25'
from app.retrieval.base import Retriever
from app.retrieval.registry import RETRIEVERS, get_retriever, register

__all__ = ["RETRIEVERS", "Retriever", "get_retriever", "register"]
