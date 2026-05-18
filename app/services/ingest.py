"""Ingest convictions into the SQLite passage store.

Orchestrates parser → repository.
"""

from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import IngestError
from app.repositories import passages as passages_repo
from app.services.parser import parse_corpus


@dataclass(frozen=True)
class IngestReport:
    documents: int
    passages: int
    orphans_deleted: int


async def ingest_corpus(session: AsyncSession, directory: Path) -> IngestReport:
    if not directory.is_dir():
        raise IngestError(f"not a directory: {directory}")

    parsed = parse_corpus(directory)
    if not parsed:
        raise IngestError(f"no passages parsed from {directory}")

    async with session.begin():
        existing = await passages_repo.all_ids(session)
        new_ids = {p.id for p in parsed}
        orphans = sorted(existing - new_ids)
        n_upserted = await passages_repo.upsert_many(session, parsed)
        n_deleted = await passages_repo.delete_ids(session, orphans)
        doc_count = await passages_repo.count_documents(session)

    return IngestReport(
        documents=doc_count,
        passages=n_upserted,
        orphans_deleted=n_deleted,
    )
