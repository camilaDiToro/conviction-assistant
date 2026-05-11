"""Admin review endpoints.

One read-only endpoint, admin-token-gated:

- ``GET /admin/conversations/{conversation_id}`` — ordered list of
  questions (one per ``kind='response'`` row) with the agent's structured
  output and step kinds.

The aggregation logic lives in :mod:`app.services.conversations`.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_admin_token
from app.api.schemas import ConversationTraceResponse
from app.config.db import get_session
from app.repositories import audit as audit_repo
from app.services import conversations as conversations_service

router = APIRouter(
    prefix="/admin/conversations",
    tags=["admin"],
    dependencies=[Depends(require_admin_token)],
)


@router.get("/{conversation_id}", response_model=ConversationTraceResponse)
async def get_conversation_trace(
    conversation_id: str,
    session: AsyncSession = Depends(get_session),
) -> ConversationTraceResponse:
    rows = await audit_repo.fetch_by_conversation(session, conversation_id)
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"conversation {conversation_id!r} not found",
        )
    return conversations_service.build_trace(conversation_id, rows)


__all__ = ["router"]
