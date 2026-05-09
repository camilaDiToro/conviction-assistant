"""Domain exceptions.

Services and repositories raise these. The API layer (`app/api/`) maps them
to HTTP responses via exception handlers registered in `app/main.py`.
Services and repositories must never raise HTTPException or reference
HTTP status codes — that's a one-way dependency from API to domain.
"""


class DomainError(Exception):
    """Base for all domain exceptions."""


class IngestError(DomainError):
    """Ingestion failed (bad directory, no parseable files, etc.)."""


class PassageNotFoundError(DomainError):
    """Raised when a tool is asked to read a passage ID that does not exist."""

    def __init__(self, passage_id: str) -> None:
        super().__init__(f"passage not found: {passage_id!r}")
        self.passage_id = passage_id


class DocumentNotFoundError(DomainError):
    """Raised when a tool is asked for a document ID that does not exist."""

    def __init__(self, document_id: str) -> None:
        super().__init__(f"document not found: {document_id!r}")
        self.document_id = document_id
