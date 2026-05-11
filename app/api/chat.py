"""POST /chat — the user-facing endpoint.

Thin handler: token-gated, receives FastAPI dependencies, delegates the
chat turn to :mod:`app.services.chat`, and returns the wire response.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_chat_token
from app.api.deps import get_llm_provider_dep
from app.api.schemas import ChatAnswerResponse, ChatClarifyResponse, ChatRequest
from app.config.db import get_session
from app.providers import LLMProvider
from app.services.chat import handle_chat_turn

router = APIRouter(tags=["chat"])


@router.post(
    "/chat",
    response_model=ChatAnswerResponse | ChatClarifyResponse,
    dependencies=[Depends(require_chat_token)],
)
async def chat(
    payload: ChatRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
    llm: LLMProvider = Depends(get_llm_provider_dep),
) -> ChatAnswerResponse | ChatClarifyResponse:
    retriever = getattr(request.app.state, "retriever", None)
    if retriever is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="retriever is not initialized",
        )
    return await handle_chat_turn(
        payload,
        session=session,
        llm=llm,
        retriever=retriever,
    )


__all__ = ["router"]
