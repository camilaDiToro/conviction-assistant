"""Read-only tools the agent can call against the conviction corpus.

The four tools (`list_documents`, `read_document_outline`,
`search_convictions` [B6], `read_passage`) are pure functions over the
repository contract. They never import a DB driver; storage swaps don't
touch this layer.

See `docs/ARCHITECTURES.md` § "Tools layer" for the architectural rules
and `docs/b5-decisions.md` for the per-tool decisions.
"""

from app.tools.context import ToolContext, ToolEntry
from app.tools.list_documents import list_documents
from app.tools.read_document_outline import read_document_outline
from app.tools.read_passage import read_passage
from app.tools.registry import (
    LIST_DOCUMENTS_DEF,
    READ_DOCUMENT_OUTLINE_DEF,
    READ_PASSAGE_DEF,
    TOOLS,
)

__all__ = [
    "LIST_DOCUMENTS_DEF",
    "READ_DOCUMENT_OUTLINE_DEF",
    "READ_PASSAGE_DEF",
    "TOOLS",
    "ToolContext",
    "ToolEntry",
    "list_documents",
    "read_document_outline",
    "read_passage",
]
