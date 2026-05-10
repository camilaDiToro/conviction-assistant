"""Chat-side conversation history — list + load endpoints.

Both endpoints are gated by ``X-Chat-Token`` (the same token the user
already pastes for ``POST /chat``). They reconstruct the user-facing
chat thread from the ``kind="response"`` rows in ``audit_log``, which
since B9 carry the verbatim ``user_question`` and the enriched
``verified_citations``.

Scope notes:

- There is no user/account model in v1. The shared chat token gates
  who can read; with one token, every browser sees every conversation
  ever created. That's the intentional v1 simplification documented in
  the production-vs-simplified roadmap section.
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
)
from app.config.db import get_session
from app.repositories import audit as audit_repo

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


def _make_title(text: str) -> str:
    text = text.strip().replace("\n", " ")
    if not text:
        return "(untitled)"
    return text if len(text) <= _TITLE_MAX else text[: _TITLE_MAX - 1] + "…"


def _message_from_payload(row: audit_repo.AuditRow, payload: dict[str, Any]) -> ConversationMessage:
    output = payload.get("output") or {}
    kind = output.get("kind", "answer")
    citations = [_citation_from_dump(c) for c in (payload.get("verified_citations") or [])]

    common = {
        "question_id": row["question_id"],
        "timestamp": row["timestamp"],  # parsed by Pydantic
        "user_question": payload.get("user_question") or payload.get("rewritten_question") or "",
        "language": payload.get("language", "en"),
        "verifier_passed": bool(payload.get("verifier_passed", False)),
    }

    if kind == "clarifying_question":
        return ConversationMessage(
            **common,
            kind="clarifying_question",
            clarifying_question=output.get("question"),
            clarifying_options=list(output.get("options") or []),
        )

    return ConversationMessage(
        **common,
        kind="answer",
        answer=output.get("answer"),
        citations=citations,
        general_knowledge_used=output.get("general_knowledge_used"),
        general_knowledge_section=output.get("general_knowledge_section"),
        out_of_scope=output.get("out_of_scope"),
    )


def _citation_from_dump(dump: dict[str, Any]) -> ChatCitation:
    """Map a serialized ``VerifiedCitation`` payload to the wire shape."""
    heading_path = list(dump.get("heading_path") or [])
    heading = heading_path[-1] if heading_path else ""
    return ChatCitation(
        passage_id=dump.get("passage_id", ""),
        document=f"{dump.get('document_id', '')}.md",
        document_updated=dump.get("document_updated"),
        heading=heading,
        heading_path=heading_path,
        quote=dump.get("quote", ""),
    )


__all__ = ["router"]
