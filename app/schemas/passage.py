from datetime import date

from pydantic import BaseModel, ConfigDict


class Passage(BaseModel):
    """A citable unit: one ## section of a conviction document."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    document_id: str
    document_title: str
    heading: str
    heading_path: list[str]
    text: str
    document_updated: date | None


class DocSummary(BaseModel):
    """Summary of one conviction document, for the list_documents tool."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    document_updated: date | None
    passage_count: int


class Heading(BaseModel):
    """One entry in a document's outline (used by read_document_outline)."""

    model_config = ConfigDict(from_attributes=True)

    passage_id: str
    heading: str
    ordinal: int


class DocumentOutline(BaseModel):
    """One document's outline, returned by the read_document_outline tool.ok"""

    model_config = ConfigDict(from_attributes=True)

    document_id: str
    document_title: str
    document_updated: date | None
    passage_count: int
    headings: list[Heading]
