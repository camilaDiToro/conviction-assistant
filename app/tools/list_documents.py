"""list_documents tool: corpus-level table of contents."""

from app.repositories import passages as passages_repo
from app.schemas import DocSummary
from app.tools.context import ToolContext


async def list_documents(ctx: ToolContext) -> list[DocSummary]:
    return await passages_repo.list_documents(ctx.session)
