"""Passage repository"""

import json
from collections.abc import Iterable
from datetime import date
from typing import Any, cast

from sqlalchemy import CursorResult, delete, func, select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.passage import PassageORM
from app.schemas.passage import DocSummary, Heading, Passage


async def upsert_many(session: AsyncSession, items: Iterable[Passage]) -> int:
    """Insert or replace passages. Idempotent.

    Ordinal is assigned by order of arrival per document_id within this call.
    Callers re-ingesting a document should pass passages in the same order
    they appear in the source file.
    """
    rows: list[dict] = []
    seen_per_doc: dict[str, int] = {}
    for p in items:
        ord_ = seen_per_doc.get(p.document_id, 0)
        seen_per_doc[p.document_id] = ord_ + 1
        rows.append(
            {
                "id": p.id,
                "document_id": p.document_id,
                "document_title": p.document_title,
                "heading": p.heading,
                "heading_path": json.dumps(p.heading_path, ensure_ascii=False),
                "text": p.text,
                "document_updated": (
                    p.document_updated.isoformat() if p.document_updated else None
                ),
                "ordinal": ord_,
            }
        )
    if not rows:
        return 0
    stmt = sqlite_insert(PassageORM).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=["id"],
        set_={
            "document_id": stmt.excluded.document_id,
            "document_title": stmt.excluded.document_title,
            "heading": stmt.excluded.heading,
            "heading_path": stmt.excluded.heading_path,
            "text": stmt.excluded.text,
            "document_updated": stmt.excluded.document_updated,
            "ordinal": stmt.excluded.ordinal,
        },
    )
    await session.execute(stmt)
    return len(rows)


async def get(session: AsyncSession, passage_id: str) -> Passage | None:
    row = await session.get(PassageORM, passage_id)
    return _orm_to_schema(row) if row else None


async def list_documents(session: AsyncSession) -> list[DocSummary]:
    stmt = (
        select(
            PassageORM.document_id,
            PassageORM.document_title,
            PassageORM.document_updated,
            func.count().label("n"),
        )
        .group_by(
            PassageORM.document_id,
            PassageORM.document_title,
            PassageORM.document_updated,
        )
        .order_by(PassageORM.document_id)
    )
    result = await session.execute(stmt)
    return [
        DocSummary(
            id=r.document_id,
            title=r.document_title,
            document_updated=(
                date.fromisoformat(r.document_updated) if r.document_updated else None
            ),
            passage_count=r.n,
        )
        for r in result.all()
    ]


async def get_document_summary(session: AsyncSession, document_id: str) -> DocSummary | None:
    """Return one document's summary, or None if it has no passages.

    Direct single-doc lookup; lets callers (e.g. the read_document_outline
    tool) check existence without scanning the whole corpus.
    """
    stmt = (
        select(
            PassageORM.document_id,
            PassageORM.document_title,
            PassageORM.document_updated,
            func.count().label("n"),
        )
        .where(PassageORM.document_id == document_id)
        .group_by(
            PassageORM.document_id,
            PassageORM.document_title,
            PassageORM.document_updated,
        )
    )
    result = await session.execute(stmt)
    row = result.one_or_none()
    if row is None:
        return None
    return DocSummary(
        id=row.document_id,
        title=row.document_title,
        document_updated=(
            date.fromisoformat(row.document_updated) if row.document_updated else None
        ),
        passage_count=row.n,
    )


async def read_outline(session: AsyncSession, document_id: str) -> list[Heading]:
    stmt = (
        select(PassageORM.id, PassageORM.heading, PassageORM.ordinal)
        .where(PassageORM.document_id == document_id)
        .order_by(PassageORM.ordinal)
    )
    result = await session.execute(stmt)
    return [Heading(passage_id=r.id, heading=r.heading, ordinal=r.ordinal) for r in result.all()]


async def all_ids(session: AsyncSession) -> set[str]:
    result = await session.execute(select(PassageORM.id))
    return set(result.scalars().all())


async def iter_all(session: AsyncSession) -> list[Passage]:
    """Bulk-load every passage with full text. Used by the BM25 index at
    startup and after re-ingest. Sorted by (document_id, ordinal) for
    deterministic indexing.
    """
    stmt = select(PassageORM).order_by(PassageORM.document_id, PassageORM.ordinal)
    result = await session.execute(stmt)
    return [_orm_to_schema(row) for row in result.scalars().all()]


async def delete_ids(session: AsyncSession, ids: Iterable[str]) -> int:
    ids_list = list(ids)
    if not ids_list:
        return 0
    stmt = delete(PassageORM).where(PassageORM.id.in_(ids_list))
    # AsyncSession.execute is typed as Result[Any]; for DML we always get a
    # CursorResult at runtime — cast so .rowcount is accessible.
    result = cast(CursorResult[Any], await session.execute(stmt))
    return result.rowcount or 0


def _orm_to_schema(p: PassageORM) -> Passage:
    return Passage(
        id=p.id,
        document_id=p.document_id,
        document_title=p.document_title,
        heading=p.heading,
        heading_path=json.loads(p.heading_path),
        text=p.text,
        document_updated=(date.fromisoformat(p.document_updated) if p.document_updated else None),
    )
