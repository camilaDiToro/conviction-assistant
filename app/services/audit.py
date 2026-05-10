"""Audit-log service — turn ``StepRecord``s into rows and write them.

Called once at end of a /chat request. The orchestrator already emits
:class:`StepRecord`s during the agent loop; this service serializes
them, stamps ``question_id`` + ``conversation_id``, and inserts in one
transaction. A final ``kind="response"`` summary row carries the per-
question header (language, retriever name, resolved citation entries,
output) so the read endpoint can render the conversation list without
rehydrating each step.

Audit writes are best-effort — if the insert fails the user response
still goes out, with a warning logged. The user response is the priority.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.schemas import StepRecord
from app.repositories import audit as audit_repo

_log = logging.getLogger(__name__)


def _serialize_step(
    step: StepRecord, *, conversation_id: str, question_id: str
) -> audit_repo.AuditRow:
    return audit_repo.AuditRow(
        step_id=step.step_id,
        question_id=question_id,
        conversation_id=conversation_id,
        timestamp=step.timestamp.isoformat(),
        kind=step.kind,
        payload=json.dumps(_step_payload(step), ensure_ascii=False),
        usage=(
            json.dumps(step.usage.model_dump(mode="json"), ensure_ascii=False)
            if step.usage is not None
            else None
        ),
    )


def _step_payload(step: StepRecord) -> dict[str, Any]:
    """Wrap the raw payload with the tool_name (when set) so a single
    JSON object covers everything we kept on the StepRecord."""
    payload = dict(step.payload)
    if step.tool_name is not None and "tool_name" not in payload:
        payload["tool_name"] = step.tool_name
    if step.duration_ms and "duration_ms" not in payload:
        payload["duration_ms"] = step.duration_ms
    return payload


def _response_row(
    *, conversation_id: str, question_id: str, summary: dict[str, Any]
) -> audit_repo.AuditRow:
    return audit_repo.AuditRow(
        step_id=str(uuid.uuid4()),
        question_id=question_id,
        conversation_id=conversation_id,
        timestamp=datetime.now(UTC).isoformat(),
        kind="response",
        payload=json.dumps(summary, ensure_ascii=False, default=str),
        usage=None,
    )


async def persist_question(
    session: AsyncSession,
    *,
    conversation_id: str,
    question_id: str,
    steps: list[StepRecord],
    response_summary: dict[str, Any],
) -> int:
    """Persist all steps + a final ``kind='response'`` summary row.

    Wraps the inserts in ``session.begin()``. On failure logs a warning
    and returns 0 — never raises out to the request handler. Returns the
    number of rows successfully inserted.
    """
    rows = [
        _serialize_step(s, conversation_id=conversation_id, question_id=question_id) for s in steps
    ]
    rows.append(
        _response_row(
            conversation_id=conversation_id,
            question_id=question_id,
            summary=response_summary,
        )
    )
    try:
        await audit_repo.insert_many(session, rows)
        await session.commit()
    except Exception:  # best-effort: never break the user's response
        await session.rollback()
        _log.exception(
            "audit_log write failed for conversation_id=%s question_id=%s",
            conversation_id,
            question_id,
        )
        return 0
    return len(rows)


__all__ = ["persist_question"]
