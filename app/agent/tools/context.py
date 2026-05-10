"""Agent runtime context — the dependency-injection seam.

``ToolContext`` is the box every agent-side helper reaches into for
runtime collaborators: an ``AsyncSession`` for the repo and a
:class:`Retriever` for ``search_convictions``. Keeping the box stable
means helper signatures don't change as dependencies are added.
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.providers import ToolDefinition
from app.retrieval import Retriever


@dataclass(frozen=True)
class ToolContext:
    """Runtime collaborators handed to every agent-side helper."""

    session: AsyncSession
    retriever: Retriever


@dataclass(frozen=True)
class ToolEntry:
    """One tool's advertisement + its callable.

    The agent loop reads ``definition`` to advertise the tool to the LLM
    and dispatches via ``func`` when the LLM asks to call it.
    """

    definition: ToolDefinition
    func: Callable[..., Awaitable[Any]]
