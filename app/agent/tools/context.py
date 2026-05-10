"""Tool dependency-injection seam.

``ToolContext`` is the box every tool reaches into for runtime
collaborators. It carries an ``AsyncSession`` (B5) and the BM25 search
index (B6). Keeping the box stable means the agent loop's
``execute_tool(name, args, ctx)`` signature does not change as
dependencies are added.
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.providers import ToolDefinition
from app.retrieval.bm25 import BM25Retriever


@dataclass(frozen=True)
class ToolContext:
    """Runtime collaborators handed to every tool function."""

    session: AsyncSession
    search_index: BM25Retriever


@dataclass(frozen=True)
class ToolEntry:
    """One tool's advertisement + its callable.

    The agent loop in B8 reads ``definition`` to advertise the tool to
    the LLM and dispatches via ``func`` when the LLM asks to call it.
    """

    definition: ToolDefinition
    func: Callable[..., Awaitable[Any]]
