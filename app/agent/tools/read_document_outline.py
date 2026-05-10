"""read_document_outline tool: one document's heading tree + metadata."""

from app.agent.tools.context import ToolContext
from app.errors import DocumentNotFoundError
from app.repositories import passages as passages_repo
from app.schemas import DocumentOutline


async def read_document_outline(ctx: ToolContext, *, document_id: str) -> DocumentOutline:
    summary = await passages_repo.get_document_summary(ctx.session, document_id)
    if summary is None:
        raise DocumentNotFoundError(document_id)
    headings = await passages_repo.read_outline(ctx.session, document_id)
    return DocumentOutline(
        document_id=document_id,
        document_title=summary.title,
        passage_count=summary.passage_count,
        headings=headings,
    )
