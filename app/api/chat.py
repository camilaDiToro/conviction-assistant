"""POST /chat — the user-facing endpoint.

Thin handler: token-gated, receives FastAPI dependencies, delegates the
chat turn to :mod:`app.services.chat`, and returns the wire response.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_chat_token
from app.api.deps import get_llm_provider_dep, get_retriever_dep
from app.api.schemas import ChatAnswerResponse, ChatClarifyResponse, ChatRequest
from app.config.db import get_session
from app.providers import LLMProvider
from app.retrieval import Retriever
from app.services.chat import handle_chat_turn

router = APIRouter(tags=["chat"])


@router.post(
    "/chat",
    response_model=ChatAnswerResponse | ChatClarifyResponse,
    dependencies=[Depends(require_chat_token)],
)
async def chat(
    payload: ChatRequest,
    session: AsyncSession = Depends(get_session),
    llm: LLMProvider = Depends(get_llm_provider_dep),
    retriever: Retriever = Depends(get_retriever_dep),
) -> ChatAnswerResponse | ChatClarifyResponse:
    return await handle_chat_turn(
        payload,
        session=session,
        llm=llm,
        retriever=retriever,
    )


__all__ = ["router"]
