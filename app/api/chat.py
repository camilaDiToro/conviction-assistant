"""POST /chat — the user-facing endpoint.

Thin handler: token-gated, parses the request, runs the agent, wraps
the result, persists the trace, returns the wire response. All business
logic lives in :mod:`app.services.wrap_response` and :mod:`app.services.audit`.

Server owns ``conversation_id`` and ``question_id`` (UUIDv4). The client
may pass a ``conversation_id`` to continue an existing thread; the
server uses it as a grouping key for the audit log without validating
existence — unknown ids simply start a new group of rows.
"""

from __future__ import annotations

import json
import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent import ConversationTurn
from app.agent import run as run_agent
from app.agent.tools import ToolContext
from app.api.auth import require_chat_token
from app.api.deps import get_llm_provider_dep
from app.api.schemas import ChatAnswerResponse, ChatClarifyResponse, ChatRequest
from app.config import settings
from app.config.db import get_session
from app.providers import LLMProvider, ProviderError, TokenUsage
from app.repositories import audit as audit_repo
from app.services import audit as audit_service
from app.services import wrap_response
from app.services.cost import compute_call_cost_usd

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
    conversation_id = payload.conversation_id or str(uuid.uuid4())
    question_id = str(uuid.uuid4())

    history = [ConversationTurn(role=t.role, content=t.content) for t in payload.history]

    prior_cost = await _prior_conversation_cost(session, conversation_id)

    tool_ctx = ToolContext(
        session=session,
        retriever=request.app.state.retriever,
    )
    result = await run_agent(payload.question, history, tool_ctx=tool_ctx, llm=llm)

    language = result.language

    response, summary = wrap_response.wrap(
        result,
        language=language,
        conversation_id=conversation_id,
        question_id=question_id,
        user_question=payload.question,
        retriever_name=settings.retrieval_strategy,
        prior_conversation_cost_usd=prior_cost,
    )

    await audit_service.persist_question(
        session,
        conversation_id=conversation_id,
        question_id=question_id,
        steps=result.steps,
        response_summary=summary,
    )

    return response


async def _prior_conversation_cost(session: AsyncSession, conversation_id: str) -> float:
    """Sum cost-USD of every LLM call already persisted for this conversation.

    Returns 0.0 for new conversations. The current question's rows are
    not yet in the table at the time we read this.
    """
    rows = await audit_repo.fetch_cost_rows_by_conversation(session, conversation_id)
    if not rows:
        return 0.0
    total = 0.0
    for row in rows:
        if not row["usage"]:
            continue
        try:
            usage = TokenUsage.model_validate(json.loads(row["usage"]))
        except (ValueError, TypeError):
            continue
        try:
            total += compute_call_cost_usd(usage)
        except ProviderError:
            # Unpriced model — drop from the rollup, not from the trace.
            continue
    return round(total, 8)


__all__ = ["router"]
