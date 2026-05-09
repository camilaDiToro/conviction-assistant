"""Tool advertisements (JSON schemas + ``ToolDefinition``s) and registry.

JSON schemas are hand-written dicts — at three tools with at most one
string field each, this is shorter and more obviously correct than
deriving them from Pydantic models. Each schema satisfies OpenAI strict
mode: every property is in ``required``, ``additionalProperties: false``,
no ``default`` values. See ``app/providers/openai.py`` ``_tool_to_openai``.
"""

from typing import Any

from app.providers import ToolDefinition
from app.tools.context import ToolEntry
from app.tools.list_documents import list_documents
from app.tools.read_document_outline import read_document_outline
from app.tools.read_passage import read_passage

LIST_DOCUMENTS_PARAMETERS: dict[str, Any] = {
    "type": "object",
    "properties": {},
    "required": [],
    "additionalProperties": False,
}

READ_DOCUMENT_OUTLINE_PARAMETERS: dict[str, Any] = {
    "type": "object",
    "properties": {
        "document_id": {
            "type": "string",
            "description": ("The document ID, as returned by list_documents (DocSummary.id)."),
        },
    },
    "required": ["document_id"],
    "additionalProperties": False,
}

READ_PASSAGE_PARAMETERS: dict[str, Any] = {
    "type": "object",
    "properties": {
        "passage_id": {
            "type": "string",
            "description": (
                "The passage ID, as returned by search_convictions or "
                "read_document_outline (Heading.passage_id)."
            ),
        },
    },
    "required": ["passage_id"],
    "additionalProperties": False,
}

LIST_DOCUMENTS_DEF = ToolDefinition(
    name="list_documents",
    description=(
        "Return all conviction documents with their titles, last-updated "
        "dates (if known), and passage counts. Use this once early in a "
        "conversation to discover what documents are available."
    ),
    parameters=LIST_DOCUMENTS_PARAMETERS,
)

READ_DOCUMENT_OUTLINE_DEF = ToolDefinition(
    name="read_document_outline",
    description=(
        "Return one document's outline: its title, last-updated date, "
        "passage count, and the ordered list of headings (each with its "
        "passage_id). Use this to find which passage in a document covers a "
        "topic before reading it."
    ),
    parameters=READ_DOCUMENT_OUTLINE_PARAMETERS,
)

READ_PASSAGE_DEF = ToolDefinition(
    name="read_passage",
    description=(
        "Return the full text of one passage by ID, plus its document title, "
        "heading path, and last-updated date. This is the only tool that "
        "returns full passage text; other tools return identifiers and outlines."
    ),
    parameters=READ_PASSAGE_PARAMETERS,
)

TOOLS: dict[str, ToolEntry] = {
    "list_documents": ToolEntry(LIST_DOCUMENTS_DEF, list_documents),
    "read_document_outline": ToolEntry(READ_DOCUMENT_OUTLINE_DEF, read_document_outline),
    "read_passage": ToolEntry(READ_PASSAGE_DEF, read_passage),
}
