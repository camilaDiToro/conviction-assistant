"""Chat-side conversation history — list + load endpoints.

Both endpoints are gated by ``X-Chat-Token`` (the same token the user
already pastes for ``POST /chat``). They reconstruct the user-facing
chat thread from the ``kind="response"`` rows in ``audit_log``, which
carry the verbatim ``user_question`` and the resolved citation entries
(passage provenance + offsets).

Scope notes:

- There is no user/account model in v1. The shared chat token gates
  who can read; with one token, every browser sees every conversation
  ever created. That's the intentional v1 simplification documented in
  the production-vs-simplified section.
- The list endpoint caps at 100 conversations; pagination is a future
  step if the corpus of conversations grows.
"""

from __future__ import annotations

import json
from typing import Any, cast

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_chat_token
from app.api.schemas import (
    ChatCitation,
    ConversationListItem,
    ConversationListResponse,
    ConversationMessage,
    ConversationMessagesResponse,
    DebugStep,
    QuestionStepsResponse,
    UsageSummary,
)
from app.config.db import get_session
from app.repositories import audit as audit_repo
from app.services.debug_view import reconstruct_steps_from_audit, response_debug_step

router = APIRouter(
    prefix="/chat/conversations",
    tags=["chat"],
    dependencies=[Depends(require_chat_token)],
)

_TITLE_MAX = 120


@router.get("", response_model=ConversationListResponse)
async def list_conversations(
    session: AsyncSession = Depends(get_session),
) -> ConversationListResponse:
    rows = await audit_repo.list_conversation_summaries(session, limit=100)
    items: list[ConversationListItem] = []
    for r in rows:
        try:
            payload = cast(dict[str, Any], json.loads(r["first_payload"]))
        except (ValueError, TypeError):
            payload = {}
        title = _make_title(payload.get("user_question") or payload.get("rewritten_question") or "")
        items.append(
            ConversationListItem(
                conversation_id=str(r["conversation_id"]),
                title=title,
                first_ts=r["first_ts"],  # type: ignore[arg-type]
                last_ts=r["last_ts"],  # type: ignore[arg-type]
                question_count=int(r["question_count"]),  # type: ignore[arg-type]
            )
        )
    return ConversationListResponse(conversations=items)


@router.get("/{conversation_id}", response_model=ConversationMessagesResponse)
async def load_conversation(
    conversation_id: str,
    session: AsyncSession = Depends(get_session),
) -> ConversationMessagesResponse:
    rows = await audit_repo.fetch_response_rows_by_conversation(session, conversation_id)
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"conversation {conversation_id!r} not found",
        )

    messages: list[ConversationMessage] = []
    for row in rows:
        try:
            payload = cast(dict[str, Any], json.loads(row["payload"]))
        except (ValueError, TypeError):
            continue
        messages.append(_message_from_payload(row, payload))
    return ConversationMessagesResponse(
        conversation_id=conversation_id,
        messages=messages,
    )


@router.get(
    "/{conversation_id}/questions/{question_id}/steps",
    response_model=QuestionStepsResponse,
)
async def question_steps(
    conversation_id: str,
    question_id: str,
    session: AsyncSession = Depends(get_session),
) -> QuestionStepsResponse:
    """Reconstruct the per-step debug trace for one historical question.

    The live ``POST /api/chat`` response inlines this as ``debug.steps``;
    when the user opens the debug drawer on a message reloaded from the
    sidebar (where ``debug.steps`` was empty), the frontend lazy-fetches
    this endpoint and hydrates the drawer with the persisted trace.
    """
    response_row = await audit_repo.fetch_response_row_by_question(
        session, conversation_id, question_id
    )
    if response_row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"question {question_id!r} in conversation {conversation_id!r} not found",
        )

    try:
        summary = cast(dict[str, Any], json.loads(response_row["payload"]))
    except (ValueError, TypeError):
        summary = {}
    retriever_name = str(summary.get("retriever") or "")

    rows = await audit_repo.fetch_steps_by_question(session, conversation_id, question_id)
    steps = reconstruct_steps_from_audit(rows, retriever_name=retriever_name)

    output_dump = summary.get("output") if isinstance(summary.get("output"), dict) else None
    if output_dump is not None:
        resolution_entries = summary.get("resolution_entries")
        if not isinstance(resolution_entries, list):
            resolution_entries = None
        steps.append(
            response_debug_step(
                output_dump,
                resolution_entries=resolution_entries,
                step_id=response_row["step_id"],
            )
        )

    return QuestionStepsResponse(
        conversation_id=conversation_id,
        question_id=question_id,
        steps=steps,
        usage_summary=_token_usage_summary(steps, duration_ms=_audit_duration_ms(rows)),
    )


def _audit_duration_ms(rows: list[audit_repo.AuditRow]) -> int:
    """Wall-clock span between first and last audit row for a question."""
    from datetime import datetime

    if not rows:
        return 0
    parsed: list[datetime] = []
    for r in rows:
        try:
            parsed.append(datetime.fromisoformat(r["timestamp"]))
        except (ValueError, TypeError):
            continue
    if not parsed:
        return 0
    delta = max(parsed) - min(parsed)
    return int(delta.total_seconds() * 1000)


def _token_usage_summary(steps: list[DebugStep], *, duration_ms: int) -> UsageSummary:
    usages = [s.usage for s in steps if s.kind == "llm_call" and s.usage is not None]
    return UsageSummary(
        llm_call_count=len(usages),
        prompt_tokens=sum(u.prompt_tokens for u in usages),
        completion_tokens=sum(u.completion_tokens for u in usages),
        cached_tokens=sum(u.cached_tokens for u in usages),
        reasoning_tokens=sum(u.reasoning_tokens for u in usages),
        step_count=len(steps),
        duration_ms=duration_ms,
    )


def _make_title(text: str) -> str:
    text = text.strip().replace("\n", " ")
    if not text:
        return "(untitled)"
    return text if len(text) <= _TITLE_MAX else text[: _TITLE_MAX - 1] + "…"


def _message_from_payload(row: audit_repo.AuditRow, payload: dict[str, Any]) -> ConversationMessage:
    output = payload.get("output") or {}
    kind = output.get("kind", "answer")
    citations = [
        chat
        for entry in (payload.get("resolution_entries") or [])
        if (chat := _citation_from_dump(entry)) is not None
    ]

    user_question_raw = payload.get("user_question") or payload.get("rewritten_question") or ""
    common = {
        "question_id": row["question_id"],
        "timestamp": row["timestamp"],  # parsed by Pydantic
        "user_question": _repair(user_question_raw) or "",
        "language": payload.get("language", "en"),
    }

    if kind == "clarifying_question":
        return ConversationMessage(
            **common,
            kind="clarifying_question",
            clarifying_question=_repair(output.get("question")),
            clarifying_options=[
                repaired
                for o in (output.get("options") or [])
                if (repaired := _repair(o)) is not None
            ],
        )

    return ConversationMessage(
        **common,
        kind="answer",
        answer=_repair(output.get("answer")),
        citations=citations,
        general_knowledge_used=output.get("general_knowledge_used"),
        general_knowledge_section=_repair(output.get("general_knowledge_section")),
        out_of_scope=output.get("out_of_scope"),
    )


def _repair(s: str | None) -> str | None:
    """Apply the broken-escape repair to historical text persisted before
    the OpenAI adapter started repairing on parse. Idempotent — strings
    that were stored cleanly are returned unchanged.

    See :func:`app.providers.text_repair.repair_broken_unicode_escapes`.
    """
    if s is None:
        return None
    from app.providers.text_repair import repair_broken_unicode_escapes

    return repair_broken_unicode_escapes(s)


def _citation_from_dump(dump: dict[str, Any]) -> ChatCitation | None:
    """Map a serialized ``CitationResolution`` payload to the wire shape.

    Entries whose passage couldn't be loaded (``passage_not_found``) are
    dropped — without ``passage_text`` there is nothing to show.
    """
    passage_text = dump.get("passage_text")
    document_id = dump.get("document_id")
    if not isinstance(passage_text, str) or not document_id:
        return None
    heading_path = list(dump.get("heading_path") or [])
    heading = heading_path[-1] if heading_path else ""
    start = dump.get("start")
    end = dump.get("end")
    return ChatCitation(
        passage_id=dump.get("passage_id", ""),
        document=f"{document_id}.md",
        heading=heading,
        heading_path=heading_path,
        passage_text=passage_text,
        start=int(start) if isinstance(start, int) else None,
        end=int(end) if isinstance(end, int) else None,
    )


__all__ = ["router"]
