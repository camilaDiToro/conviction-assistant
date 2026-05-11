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

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent import AgentOverrides, ConversationTurn
from app.agent import run as run_agent
from app.agent.tools import ToolContext
from app.api.auth import require_chat_token
from app.api.deps import get_llm_provider_dep
from app.api.schemas import ChatAnswerResponse, ChatClarifyResponse, ChatRequest
from app.config import settings
from app.config.db import get_session
from app.providers import LLMProvider, ProviderError, TokenUsage, get_llm_provider
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

    overrides_payload = payload.overrides
    agent_overrides: AgentOverrides | None = None
    if overrides_payload is not None:
        if (
            overrides_payload.model is not None
            and overrides_payload.model not in settings.allowed_models
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"model {overrides_payload.model!r} is not in allowed_models",
            )
        if overrides_payload.model and overrides_payload.model != settings.openai_model:
            # Rebind the LLM provider to the override model. The default
            # provider was already constructed by the Depends; we throw
            # it away in this branch only.
            llm = get_llm_provider(model=overrides_payload.model)
        agent_overrides = AgentOverrides(
            reasoning_effort=overrides_payload.reasoning_effort,
            rewrite_reasoning_effort=overrides_payload.rewrite_reasoning_effort,
            agent_max_tool_calls=overrides_payload.agent_max_tool_calls,
            agent_max_output_tokens=overrides_payload.agent_max_output_tokens,
        )

    prior_cost = await _prior_conversation_cost(session, conversation_id)

    tool_ctx = ToolContext(
        session=session,
        retriever=request.app.state.retriever,
    )
    result = await run_agent(
        payload.question, history, tool_ctx=tool_ctx, llm=llm, overrides=agent_overrides
    )

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
