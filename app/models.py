from datetime import date

from pydantic import BaseModel


class Passage(BaseModel):
    """A citable unit: one ## section of a conviction document."""

    id: str
    document_id: str
    document_title: str
    heading: str
    heading_path: list[str]
    text: str
    document_updated: date | None
