"""Tool advertisements (JSON schemas + ``ToolDefinition``s) and registry.

JSON schemas are hand-written dicts — at three tools with at most one
string field each, this is shorter and more obviously correct than
deriving them from Pydantic models. Each schema satisfies OpenAI strict
mode: every property is in ``required``, ``additionalProperties: false``,
no ``default`` values. See ``app/providers/openai.py`` ``_tool_to_openai``.
"""

from typing import Any

from app.agent.tools.context import ToolEntry
from app.agent.tools.list_documents import list_documents
from app.agent.tools.read_document_outline import read_document_outline
from app.agent.tools.read_passage import read_passage
from app.agent.tools.search_convictions import search_convictions
from app.providers import ToolDefinition

LIST_DOCUMENTS_PARAMETERS: dict[str, Any] = {
    "type": "object",
    "properties": {
        "k": {
            "type": "integer",
            "description": (
                "Maximum number of documents to return, ordered by "
                "document_id. Pass a value large enough to cover the "
                "corpus (e.g. 30) when you want the full table of contents."
            ),
        },
    },
    "required": ["k"],
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
        "passage_ids": {
            "type": "array",
            "items": {"type": "string"},
            "description": (
                "One or more passage IDs, as returned by search_convictions "
                "or read_document_outline (Heading.passage_id). Batch every "
                "passage you intend to cite in a single call rather than "
                "issuing one tool call per ID."
            ),
        },
    },
    "required": ["passage_ids"],
    "additionalProperties": False,
}

SEARCH_CONVICTIONS_PARAMETERS: dict[str, Any] = {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": (
                "Free-text query in the user's language (PT, EN, or ES). "
                "BM25 ranking with accent-stripped, lowercase tokenization. "
                "Use specific terms (asset names, regulations, headings) "
                "rather than long paraphrases."
            ),
        },
        "k": {
            "type": "integer",
            "description": (
                "Number of top hits to return. Pass 5 unless you have a "
                "reason to change it; larger k dilutes precision."
            ),
        },
    },
    "required": ["query", "k"],
    "additionalProperties": False,
}

LIST_DOCUMENTS_DEF = ToolDefinition(
    name="list_documents",
    description=(
        "Return up to k conviction documents with their titles and passage "
        "counts, ordered by document_id. Use this once early in a "
        "conversation to discover what documents are available."
    ),
    parameters=LIST_DOCUMENTS_PARAMETERS,
)

READ_DOCUMENT_OUTLINE_DEF = ToolDefinition(
    name="read_document_outline",
    description=(
        "Return one document's outline: its title, passage count, and the "
        "ordered list of headings (each with its passage_id). Use this to "
        "find which passage in a document covers a topic before reading it."
    ),
    parameters=READ_DOCUMENT_OUTLINE_PARAMETERS,
)

READ_PASSAGE_DEF = ToolDefinition(
    name="read_passage",
    description=(
        "Return the full text of one or more passages by ID, each with its "
        "document title and heading path. Pass every ID you intend to cite "
        "in a single call — the result is a list aligned to the input "
        "order. This is the only tool that returns full passage text; "
        "other tools return identifiers and outlines."
    ),
    parameters=READ_PASSAGE_PARAMETERS,
)

SEARCH_CONVICTIONS_DEF = ToolDefinition(
    name="search_convictions",
    description=(
        "Search the conviction corpus by free-text query and return the "
        "top-k matching passages, each with a short snippet, document "
        "title, heading path, and BM25 score. Call this first to find "
        "relevant evidence; then call read_passage for the full text of "
        "any hit you want to cite."
    ),
    parameters=SEARCH_CONVICTIONS_PARAMETERS,
)

TOOLS: dict[str, ToolEntry] = {
    "list_documents": ToolEntry(LIST_DOCUMENTS_DEF, list_documents),
    "read_document_outline": ToolEntry(READ_DOCUMENT_OUTLINE_DEF, read_document_outline),
    "search_convictions": ToolEntry(SEARCH_CONVICTIONS_DEF, search_convictions),
    "read_passage": ToolEntry(READ_PASSAGE_DEF, read_passage),
}
