"""Admin review endpoints for B9.

Two read-only endpoints, both admin-token-gated:

- ``GET /admin/conversations/{conversation_id}`` — ordered list of
  questions (one per ``kind='response'`` row) with the agent's structured
  output and step kinds. Lets reviewers see *what the agent did* without
  opening the SQLite file.
- ``GET /admin/conversations/{conversation_id}/cost`` — same scope but
  rolled up by question with token totals and USD cost (computed via
  :mod:`app.services.cost` from the persisted ``TokenUsage``).

Both return 404 when the conversation has no rows. Steps are not
expanded into individual entries here — the response carries
``step_count`` + ``step_kinds`` per question, which is enough for review.
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime
from typing import Any, cast

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_admin_token
from app.api.schemas import (
    ConversationCostQuestion,
    ConversationCostResponse,
    ConversationQuestionSummary,
    ConversationTraceResponse,
)
from app.config.db import get_session
from app.providers import ProviderError, TokenUsage
from app.repositories import audit as audit_repo
from app.services.cost import compute_call_cost_usd

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

    by_question: dict[str, list[audit_repo.AuditRow]] = defaultdict(list)
    for row in rows:
        by_question[row["question_id"]].append(row)

    # Order questions by the timestamp of their first row.
    question_ids = sorted(by_question, key=lambda qid: by_question[qid][0]["timestamp"])

    questions: list[ConversationQuestionSummary] = []
    for qid in question_ids:
        question_rows = by_question[qid]
        response_row = _find_response_row(question_rows)
        if response_row is None:
            # No summary row — partial write or in-flight question.
            # Skip rather than fabricate a summary.
            continue
        summary_payload = cast(dict[str, Any], json.loads(response_row["payload"]))
        non_response_rows = [r for r in question_rows if r["kind"] != "response"]
        questions.append(
            ConversationQuestionSummary(
                question_id=qid,
                timestamp=datetime.fromisoformat(response_row["timestamp"]),
                language=summary_payload.get("language", "en"),
                rewritten_question=summary_payload.get("rewritten_question"),
                answer_or_question=summary_payload.get("output", {}),
                verifier_passed=bool(summary_payload.get("verifier_passed", False)),
                step_count=len(non_response_rows),
                step_kinds=[r["kind"] for r in non_response_rows],
                retriever=summary_payload.get("retriever", ""),
                verifier_strategy=summary_payload.get("verifier_strategy", ""),
            )
        )

    return ConversationTraceResponse(
        conversation_id=conversation_id,
        questions=questions,
        step_count_total=len(rows),
    )


@router.get("/{conversation_id}/cost", response_model=ConversationCostResponse)
async def get_conversation_cost(
    conversation_id: str,
    session: AsyncSession = Depends(get_session),
) -> ConversationCostResponse:
    rows = await audit_repo.fetch_cost_rows_by_conversation(session, conversation_id)
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"conversation {conversation_id!r} not found",
        )

    by_question: dict[str, list[audit_repo.AuditRow]] = defaultdict(list)
    for row in rows:
        by_question[row["question_id"]].append(row)

    # Order by first row's timestamp per question.
    question_ids = sorted(by_question, key=lambda qid: by_question[qid][0]["timestamp"])

    questions: list[ConversationCostQuestion] = []
    total_cost = 0.0
    total_calls = 0
    for qid in question_ids:
        prompt = completion = cached = reasoning = 0
        cost = 0.0
        for row in by_question[qid]:
            if not row["usage"]:
                continue
            try:
                usage = TokenUsage.model_validate(json.loads(row["usage"]))
            except (ValueError, TypeError):
                continue
            prompt += usage.prompt_tokens
            completion += usage.completion_tokens
            cached += usage.cached_tokens
            reasoning += usage.reasoning_tokens
            try:
                cost += compute_call_cost_usd(usage)
            except ProviderError:
                # Unpriced model — keep the token totals visible but skip the cost.
                continue
        questions.append(
            ConversationCostQuestion(
                question_id=qid,
                llm_call_count=len(by_question[qid]),
                prompt_tokens=prompt,
                completion_tokens=completion,
                cached_tokens=cached,
                reasoning_tokens=reasoning,
                cost_usd=round(cost, 8),
            )
        )
        total_cost += cost
        total_calls += len(by_question[qid])

    return ConversationCostResponse(
        conversation_id=conversation_id,
        questions=questions,
        total_cost_usd=round(total_cost, 8),
        total_llm_calls=total_calls,
    )


def _find_response_row(rows: list[audit_repo.AuditRow]) -> audit_repo.AuditRow | None:
    for row in rows:
        if row["kind"] == "response":
            return row
    return None


__all__ = ["router"]
