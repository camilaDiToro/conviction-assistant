"""BM25 search index over the conviction corpus.

Built at startup from `passages_repo.iter_all()`; rebuilt at the end of
`POST /admin/ingest`.

Tokenization:
- NFKD unicode normalization, drop combining marks (accent-strip)
- lowercase
- collapse runs of whitespace to a single space
- split via `bm25s.tokenize` defaults (regex on `\\W+`)
- no stopwords, no stemmer

The same pipeline runs against indexed passages and incoming queries.
Diacritic-stripping at the search layer is independent of the offset
resolver, which operates on the raw passage text so cited quotes
round-trip: search normalization is a recall concern, resolver matching
is a fidelity concern.
"""

import re
import unicodedata

import bm25s  # type: ignore[import-untyped]
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import passages as passages_repo
from app.schemas.passage import Passage

_WHITESPACE_RE = re.compile(r"\s+")


def _normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    no_accents = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return _WHITESPACE_RE.sub(" ", no_accents.lower()).strip()


class BM25Retriever:
    """In-memory BM25 retriever over conviction passages.

    A single instance lives on `app.state.retriever`. Lifespan calls
    `build()`; admin ingest calls `rebuild()`. Tests construct one, seed
    the DB, call `build()`, and pass the index into `ToolContext`.
    """

    def __init__(self) -> None:
        self._passages: list[Passage] = []
        self._retriever: bm25s.BM25 | None = None

    async def build(self, session: AsyncSession) -> None:
        passages = await passages_repo.iter_all(session)
        self._reindex(passages)

    async def rebuild(self, session: AsyncSession) -> None:
        await self.build(session)

    def _reindex(self, passages: list[Passage]) -> None:
        # Build the new retriever in locals first; commit both refs in one
        # statement so a tokenize/index failure leaves the prior index serving.
        if not passages:
            self._passages, self._retriever = [], None
            return
        corpus = [_normalize(p.text) for p in passages]
        tokens = bm25s.tokenize(corpus, stopwords=None, show_progress=False)
        retriever = bm25s.BM25()
        retriever.index(tokens, show_progress=False)
        self._passages, self._retriever = passages, retriever

    def search(self, query: str, k: int) -> list[tuple[Passage, float]]:
        """Return the top-`k` (passage, score) pairs for `query`.

        Empty / whitespace-only queries are caller-side — the tool wrapper
        raises `EmptyQueryError` before getting here. Empty-corpus and
        unbuilt-index both return `[]`.
        """
        if self._retriever is None or not self._passages:
            return []
        normalized = _normalize(query)
        if not normalized:
            return []
        query_tokens = bm25s.tokenize([normalized], stopwords=None, show_progress=False)
        k_eff = min(k, len(self._passages))
        # No `corpus=` argument: bm25s returns the integer doc indices into
        # the indexed array, which is the same order as `self._passages`.
        results, scores = self._retriever.retrieve(query_tokens, k=k_eff, show_progress=False)
        out: list[tuple[Passage, float]] = []
        for i in range(results.shape[1]):
            idx = int(results[0, i])
            score = float(scores[0, i])
            out.append((self._passages[idx], score))
        return out
