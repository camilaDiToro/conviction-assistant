"""read_passage tool: full text of one passage by ID."""

from app.agent.tools.context import ToolContext
from app.errors import PassageNotFoundError
from app.repositories import passages as passages_repo
from app.schemas import Passage


async def read_passage(ctx: ToolContext, *, passage_id: str) -> Passage:
    passage = await passages_repo.get(ctx.session, passage_id)
    if passage is None:
        raise PassageNotFoundError(passage_id)
    return passage
