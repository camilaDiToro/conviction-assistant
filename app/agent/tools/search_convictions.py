"""search_convictions tool: BM25 retrieval over the conviction corpus."""

from app.agent.tools.context import ToolContext
from app.errors import EmptyQueryError
from app.retrieval.bm25 import _make_snippet
from app.schemas import PassageHit


async def search_convictions(
    ctx: ToolContext,
    *,
    query: str,
    k: int = 5,
) -> list[PassageHit]:
    if not query or not query.strip():
        raise EmptyQueryError()
    pairs = ctx.retriever.search(query, k=k)
    return [
        PassageHit(
            passage_id=p.id,
            score=score,
            document_id=p.document_id,
            document_title=p.document_title,
            heading_path=p.heading_path,
            snippet=_make_snippet(p.text),
        )
        for p, score in pairs
    ]
