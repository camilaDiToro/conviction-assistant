"""Read-only tools the agent can call against the conviction corpus.

The four tools (`list_documents`, `read_document_outline`,
`search_convictions`, `read_passage`) are pure functions over the
repository contract. They never import a DB driver; storage swaps don't
touch this layer.

See `docs/ARCHITECTURES.md` § "Tools layer" for the architectural rules,
`docs/b5-decisions.md` for the simple-tool decisions, and
`docs/b6-decisions.md` for `search_convictions` decisions.
"""

from app.agent.tools.context import ToolContext, ToolEntry
from app.agent.tools.list_documents import list_documents
from app.agent.tools.read_document_outline import read_document_outline
from app.agent.tools.read_passage import read_passage
from app.agent.tools.registry import (
    LIST_DOCUMENTS_DEF,
    READ_DOCUMENT_OUTLINE_DEF,
    READ_PASSAGE_DEF,
    SEARCH_CONVICTIONS_DEF,
    TOOLS,
)
from app.agent.tools.search_convictions import search_convictions

__all__ = [
    "LIST_DOCUMENTS_DEF",
    "READ_DOCUMENT_OUTLINE_DEF",
    "READ_PASSAGE_DEF",
    "SEARCH_CONVICTIONS_DEF",
    "TOOLS",
    "ToolContext",
    "ToolEntry",
    "list_documents",
    "read_document_outline",
    "read_passage",
    "search_convictions",
]
