"""Pure mapping: ``AgentResult`` → wire ``ChatResponse`` + audit summary.

This service has no side effects. Given the agent's structured result and
the request-level identifiers, it produces:

1. The wire response (``ChatAnswerResponse`` or ``ChatClarifyResponse``)
   the HTTP handler returns to the client.
2. A summary dict the caller stores as the ``kind='response'`` audit row.

Citation enrichment uses the ``CitationResolution`` entries the agent
already produced — no extra DB hits at response time. Token usage is
kept as raw provider counts.

Debug-drawer formatting (per-step name/detail/result, the synthetic
response step, and the historical reconstruction path) lives in
:mod:`app.services.debug_view`.
"""

from typing import Any

from app.agent import AgentResult, AnswerOutput, ClarifyingQuestionOutput, StepRecord
from app.agent.resolver import CitationResolution
from app.api.schemas import (
    ChatAnswerResponse,
    ChatCitation,
    ChatClarifyResponse,
    DebugBlock,
    UsageSummary,
)
from app.i18n import Language
from app.services.debug_view import response_debug_step, step_to_debug
from app.services.disclaimer import disclaimer_for


def wrap(
    result: AgentResult,
    *,
    language: Language,
    conversation_id: str,
    question_id: str,
    user_question: str,
    retriever_name: str,
) -> tuple[ChatAnswerResponse | ChatClarifyResponse, dict[str, Any]]:
    """Wrap one agent turn into the wire response + the audit summary.

    ``user_question`` is the verbatim text the user sent — persisted in
    the audit summary so the conversation list endpoint can render a
    title without re-running the agent.
    """
    resolution_entries = list(result.resolution.entries) if result.resolution else []
    debug_steps = [step_to_debug(s, retriever_name) for s in result.steps]

    debug_steps.append(
        response_debug_step(
            result.output.model_dump(mode="json"),
            resolution_entries=[e.model_dump(mode="json") for e in resolution_entries],
        )
    )

    usage_summary = _usage_summary(result, step_count=len(debug_steps))
    debug = DebugBlock(
        tool_calls=[d for d in debug_steps if d.kind == "tool_call"],
        steps=debug_steps,
    )

    if isinstance(result.output, ClarifyingQuestionOutput):
        response: ChatAnswerResponse | ChatClarifyResponse = ChatClarifyResponse(
            question=result.output.question,
            options=list(result.output.options),
            disclaimer=disclaimer_for(language),
            usage_summary=usage_summary,
            debug=debug,
            conversation_id=conversation_id,
            question_id=question_id,
        )
    else:
        citations = [
            chat for e in resolution_entries if (chat := _resolution_to_chat(e)) is not None
        ]
        response = ChatAnswerResponse(
            answer=result.output.answer,
            citations=citations,
            general_knowledge_used=result.output.general_knowledge_used,
            general_knowledge_section=result.output.general_knowledge_section,
            out_of_scope=result.output.out_of_scope,
            disclaimer=disclaimer_for(language),
            usage_summary=usage_summary,
            debug=debug,
            conversation_id=conversation_id,
            question_id=question_id,
        )

    summary = _audit_summary(
        result=result,
        language=language,
        user_question=user_question,
        retriever_name=retriever_name,
        resolution_entries=resolution_entries,
    )
    return response, summary


def _resolution_to_chat(entry: CitationResolution) -> ChatCitation | None:
    """Convert one resolution entry into a wire ``ChatCitation``.

    Citations whose passage couldn't be loaded (``passage_not_found``)
    are dropped — without ``passage_text`` there is nothing to show.
    All other entries surface; ``start`` / ``end`` are ``None`` when the
    quote did not anchor.
    """
    if entry.passage_text is None or entry.document_id is None:
        return None
    heading = entry.heading_path[-1] if entry.heading_path else ""
    return ChatCitation(
        passage_id=entry.passage_id,
        document=f"{entry.document_id}.md",
        heading=heading,
        heading_path=list(entry.heading_path),
        passage_text=entry.passage_text,
        start=entry.start,
        end=entry.end,
    )


def _question_duration_ms(steps: list[StepRecord]) -> int:
    """Wall-clock span between the first and last persisted step.

    Returns 0 for an empty trace. Drives the ``duration_ms`` field on
    ``UsageSummary`` — used to render total time-spent in the debug
    drawer's summary section.
    """
    if not steps:
        return 0
    timestamps = [s.timestamp for s in steps]
    delta = max(timestamps) - min(timestamps)
    return int(delta.total_seconds() * 1000)


def _usage_summary(result: AgentResult, *, step_count: int) -> UsageSummary:
    totals = result.token_totals
    return UsageSummary(
        llm_call_count=totals.llm_call_count,
        prompt_tokens=totals.prompt_tokens,
        completion_tokens=totals.completion_tokens,
        cached_tokens=totals.cached_tokens,
        reasoning_tokens=totals.reasoning_tokens,
        step_count=step_count,
        duration_ms=_question_duration_ms(result.steps),
    )


def _audit_summary(
    *,
    result: AgentResult,
    language: Language,
    user_question: str,
    retriever_name: str,
    resolution_entries: list[CitationResolution],
) -> dict[str, Any]:
    output = result.output
    summary: dict[str, Any] = {
        "language": language,
        "user_question": user_question,
        "rewritten_question": result.rewritten_question,
        "tool_call_count": result.tool_call_count,
        "search_count": result.search_count,
        "retriever": retriever_name,
        "step_count": len(result.steps),
        "step_kinds": [s.kind for s in result.steps],
        "output": output.model_dump(mode="json"),
        # Enriched citation provenance + offsets — lets the conversation-
        # load endpoint render the same chips as the live response.
        "resolution_entries": [e.model_dump(mode="json") for e in resolution_entries],
    }
    if isinstance(output, AnswerOutput):
        summary["out_of_scope"] = output.out_of_scope
        summary["general_knowledge_used"] = output.general_knowledge_used
    return summary


__all__ = ["wrap"]
