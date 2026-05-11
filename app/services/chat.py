"""Chat turn orchestration.

The API layer owns HTTP concerns. This service owns the application flow:
prepare IDs and history, run the agent, wrap the wire response, and persist
the audit trace.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.agent import ConversationTurn
from app.agent import run as run_agent
from app.agent.tools import ToolContext
from app.api.schemas import ChatAnswerResponse, ChatClarifyResponse, ChatRequest
from app.config import settings
from app.providers import LLMProvider
from app.retrieval import Retriever
from app.services import audit as audit_service
from app.services import wrap_response


async def handle_chat_turn(
    payload: ChatRequest,
    *,
    session: AsyncSession,
    llm: LLMProvider,
    retriever: Retriever,
) -> ChatAnswerResponse | ChatClarifyResponse:
    conversation_id = payload.conversation_id or str(uuid.uuid4())
    question_id = str(uuid.uuid4())
    history = [ConversationTurn(role=t.role, content=t.content) for t in payload.history]

    tool_ctx = ToolContext(session=session, retriever=retriever)
    result = await run_agent(payload.question, history, tool_ctx=tool_ctx, llm=llm)

    response, summary = wrap_response.wrap(
        result,
        language=result.language,
        conversation_id=conversation_id,
        question_id=question_id,
        user_question=payload.question,
        retriever_name=settings.retrieval_strategy,
    )

    await audit_service.persist_question(
        session,
        conversation_id=conversation_id,
        question_id=question_id,
        steps=result.steps,
        response_summary=summary,
    )

    return response


__all__ = ["handle_chat_turn"]
