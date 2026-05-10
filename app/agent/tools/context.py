"""Agent runtime context — the dependency-injection seam.

``ToolContext`` is the box every agent-side helper reaches into for
runtime collaborators: an ``AsyncSession`` for the repo, a
:class:`Retriever` for ``search_convictions``, a :class:`Verifier` for
the citation check. Keeping the box stable means helper signatures
don't change as dependencies are added.
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.verifier import SubstringVerifier, Verifier
from app.providers import ToolDefinition
from app.retrieval import Retriever


@dataclass(frozen=True)
class ToolContext:
    """Runtime collaborators handed to every agent-side helper.

    ``verifier`` defaults to a fresh :class:`SubstringVerifier` — the
    architectural commitment. Production wiring (B9 chat endpoint)
    passes ``app.state.verifier`` (chosen via ``settings.verifier_strategy``).
    """

    session: AsyncSession
    retriever: Retriever
    verifier: Verifier = field(default_factory=SubstringVerifier)


@dataclass(frozen=True)
class ToolEntry:
    """One tool's advertisement + its callable.

    The agent loop reads ``definition`` to advertise the tool to the LLM
    and dispatches via ``func`` when the LLM asks to call it.
    """

    definition: ToolDefinition
    func: Callable[..., Awaitable[Any]]
