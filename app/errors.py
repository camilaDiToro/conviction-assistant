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
