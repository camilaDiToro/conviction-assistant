"""Ingest convictions into the SQLite passage store.

Orchestrates parser → repository. Returns a domain object; HTTP concerns
live in app/api/admin.py. Renamed-heading caveat: passage IDs are
slug-based, so renaming a heading produces a new ID and the previous ID
becomes an orphan. We delete orphans on re-ingest and surface the count
so the caller can notice.

Parser is sync (pure markdown → list[Passage]); calling it from this
async function blocks the event loop while parsing. For 30 small files
this is sub-second and not worth offloading to a thread executor.
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
        # Count distinct documents inside the same transaction — reading
        # after commit would autobegin a new transaction the caller
        # couldn't close.
        doc_count = await passages_repo.count_documents(session)

    return IngestReport(
        documents=doc_count,
        passages=n_upserted,
        orphans_deleted=n_deleted,
    )
