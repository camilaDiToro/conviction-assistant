"""list_documents tool: corpus-level table of contents."""

from app.agent.tools.context import ToolContext
from app.repositories import passages as passages_repo
from app.schemas import DocSummary


async def list_documents(ctx: ToolContext, *, k: int) -> list[DocSummary]:
    return await passages_repo.list_documents(ctx.session, limit=k)
