"""read_passage tool: full text of one or more passages by ID."""

from app.agent.tools.context import ToolContext
from app.errors import PassageNotFoundError
from app.repositories import passages as passages_repo
from app.schemas import Passage


async def read_passage(ctx: ToolContext, *, passage_ids: list[str]) -> list[Passage]:
    found = await passages_repo.get_many(ctx.session, passage_ids)
    for pid in passage_ids:
        if pid not in found:
            raise PassageNotFoundError(pid)
    return [found[pid] for pid in passage_ids]
