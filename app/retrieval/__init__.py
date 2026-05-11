"""Retrieval strategies — Protocol + registry.

The single contract is :class:`Retriever`. Today's only registered
strategy is ``bm25``; the documented level-up is hybrid (BM25 + dense
+ RRF). A new strategy = drop a file in, add an entry to
``_RETRIEVERS`` in ``registry.py``, widen ``settings.retrieval_strategy``.
No edit to call sites.
"""

from app.retrieval.base import Retriever
from app.retrieval.registry import available_retrievers, get_retriever
from app.retrieval.snippet import make_snippet

__all__ = ["Retriever", "available_retrievers", "get_retriever", "make_snippet"]
