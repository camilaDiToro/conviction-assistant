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

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_chat_token
from app.api.schemas import (
    ConversationListResponse,
    ConversationMessage,
    ConversationMessagesResponse,
    QuestionStepsResponse,
)
from app.config.db import get_session
from app.repositories import audit as audit_repo
from app.services.chat_history import (
    list_item_from_summary_row,
    message_from_response_row,
    steps_response_from_rows,
)

router = APIRouter(
    prefix="/chat/conversations",
    tags=["chat"],
    dependencies=[Depends(require_chat_token)],
)


@router.get("", response_model=ConversationListResponse)
async def list_conversations(
    session: AsyncSession = Depends(get_session),
) -> ConversationListResponse:
    rows = await audit_repo.list_conversation_summaries(session, limit=100)
    return ConversationListResponse(
        conversations=[list_item_from_summary_row(r) for r in rows],
    )


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
        message = message_from_response_row(row)
        if message is not None:
            messages.append(message)
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
    step_rows = await audit_repo.fetch_steps_by_question(session, conversation_id, question_id)
    return steps_response_from_rows(
        response_row,
        step_rows,
        conversation_id=conversation_id,
        question_id=question_id,
    )


__all__ = ["router"]
