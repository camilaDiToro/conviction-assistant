"""Audit-log repository — the only place audit_log SQL lives.

The schema lives in ``alembic/versions/0001_initial_schema.py``; this
module exposes the typed async functions that services call.
"""

from collections.abc import Iterable
from typing import TypedDict

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLogORM


class AuditRow(TypedDict):
    """One persisted audit row, as returned by the read functions."""

    step_id: str
    question_id: str
    conversation_id: str
    timestamp: str
    kind: str
    payload: str
    usage: str | None


class ConversationSummaryRow(TypedDict):
    """One aggregated row from :func:`list_conversation_summaries`."""

    conversation_id: str
    first_ts: str
    last_ts: str
    question_count: int
    first_payload: str


async def insert_many(session: AsyncSession, rows: Iterable[AuditRow]) -> int:
    """Insert N audit rows in one round-trip. Idempotent only by
    ``step_id`` PK — duplicate ``step_id``s raise IntegrityError.
    """
    rows_list = list(rows)
    if not rows_list:
        return 0
    session.add_all([AuditLogORM(**row) for row in rows_list])
    await session.flush()
    return len(rows_list)


async def fetch_by_conversation(session: AsyncSession, conversation_id: str) -> list[AuditRow]:
    stmt = (
        select(AuditLogORM)
        .where(AuditLogORM.conversation_id == conversation_id)
        .order_by(AuditLogORM.timestamp, AuditLogORM.step_id)
    )
    result = await session.execute(stmt)
    return [_orm_to_row(row) for row in result.scalars().all()]


async def fetch_steps_by_question(
    session: AsyncSession, conversation_id: str, question_id: str
) -> list[AuditRow]:
    """Read non-response rows for one (conversation_id, question_id),
    ordered by SQLite ``rowid`` (insertion order). Drives the per-question
    step drawer for historical messages.

    ``rowid`` (not ``timestamp``) is the right key here: agent steps are
    emitted in fast succession and ``datetime.now()`` resolution on
    Windows is coarse enough to tie, after which a step_id-UUID tiebreak
    randomizes the ordering. Insertion order is what the live trace
    reflects, so use it on read too.
    """
    stmt = (
        select(AuditLogORM)
        .where(
            AuditLogORM.conversation_id == conversation_id,
            AuditLogORM.question_id == question_id,
            AuditLogORM.kind != "response",
        )
        .order_by(text("rowid"))
    )
    result = await session.execute(stmt)
    return [_orm_to_row(row) for row in result.scalars().all()]


async def fetch_response_row_by_question(
    session: AsyncSession, conversation_id: str, question_id: str
) -> AuditRow | None:
    """Fetch the single ``kind='response'`` row for one (cid, qid). The
    payload carries the ``retriever`` used — needed to regenerate
    ``DebugStep.name``/``detail`` for the historical drawer.
    """
    stmt = (
        select(AuditLogORM)
        .where(
            AuditLogORM.conversation_id == conversation_id,
            AuditLogORM.question_id == question_id,
            AuditLogORM.kind == "response",
        )
        .order_by(AuditLogORM.timestamp, AuditLogORM.step_id)
        .limit(1)
    )
    result = await session.execute(stmt)
    row = result.scalars().first()
    return _orm_to_row(row) if row is not None else None


async def fetch_response_rows_by_conversation(
    session: AsyncSession, conversation_id: str
) -> list[AuditRow]:
    """Read only the ``kind='response'`` rows for one conversation,
    ordered by timestamp. Each row carries the per-question summary
    (user_question, output, resolution_entries, language) used to
    rebuild the chat thread.
    """
    stmt = (
        select(AuditLogORM)
        .where(
            AuditLogORM.conversation_id == conversation_id,
            AuditLogORM.kind == "response",
        )
        .order_by(AuditLogORM.timestamp, AuditLogORM.step_id)
    )
    result = await session.execute(stmt)
    return [_orm_to_row(row) for row in result.scalars().all()]


async def list_conversation_summaries(
    session: AsyncSession, *, limit: int = 100
) -> list[ConversationSummaryRow]:
    """Return one row per ``conversation_id`` with the first/latest
    response timestamps, ordered most-recent-first. The first response's
    ``payload.user_question`` is used as a title; the LIMIT caps how many
    threads the sidebar fetches at once.
    """
    stmt = text(
        "SELECT conversation_id, MIN(timestamp) AS first_ts, "
        "MAX(timestamp) AS last_ts, COUNT(*) AS question_count "
        "FROM audit_log WHERE kind = 'response' "
        "GROUP BY conversation_id "
        "ORDER BY last_ts DESC "
        "LIMIT :lim"
    )
    summaries = (await session.execute(stmt, {"lim": limit})).all()

    if not summaries:
        return []

    # Pull the first-row payload per conversation in one query.
    conv_ids = [r.conversation_id for r in summaries]
    placeholders = ",".join(f":c{i}" for i in range(len(conv_ids)))
    params = {f"c{i}": cid for i, cid in enumerate(conv_ids)}
    titles_stmt = text(
        f"SELECT a.conversation_id, a.payload "
        f"FROM audit_log a "
        f"JOIN ( "
        f"  SELECT conversation_id, MIN(timestamp) AS first_ts "
        f"  FROM audit_log WHERE kind='response' "
        f"  AND conversation_id IN ({placeholders}) "
        f"  GROUP BY conversation_id "
        f") f ON a.conversation_id = f.conversation_id "
        f"AND a.timestamp = f.first_ts "
        f"WHERE a.kind = 'response'"
    )
    title_rows = (await session.execute(titles_stmt, params)).all()
    payload_by_conv = {r.conversation_id: r.payload for r in title_rows}

    return [
        ConversationSummaryRow(
            conversation_id=r.conversation_id,
            first_ts=r.first_ts,
            last_ts=r.last_ts,
            question_count=r.question_count,
            first_payload=payload_by_conv.get(r.conversation_id, "{}"),
        )
        for r in summaries
    ]


def _orm_to_row(orm: AuditLogORM) -> AuditRow:
    return AuditRow(
        step_id=orm.step_id,
        question_id=orm.question_id,
        conversation_id=orm.conversation_id,
        timestamp=orm.timestamp,
        kind=orm.kind,
        payload=orm.payload,
        usage=orm.usage,
    )


__all__ = [
    "AuditRow",
    "ConversationSummaryRow",
    "fetch_by_conversation",
    "fetch_response_rows_by_conversation",
    "fetch_response_row_by_question",
    "fetch_steps_by_question",
    "insert_many",
    "list_conversation_summaries",
]
