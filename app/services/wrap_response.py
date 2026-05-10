"""Pure mapping: ``AgentResult`` → wire ``ChatResponse`` + audit summary.

This service has no side effects. Given the agent's structured result and
the request-level identifiers, it produces:

1. The wire response (``ChatAnswerResponse`` or ``ChatClarifyResponse``)
   the HTTP handler returns to the client.
2. A summary dict the caller stores as the ``kind='response'`` audit row.

Citation enrichment uses the ``VerifiedCitation`` provenance the agent
already produced — no extra DB hits at response time. Cost is computed
per LLM-call step via :func:`app.services.cost.compute_call_cost_usd`.
"""

from typing import Any

from app.agent import AgentResult, AnswerOutput, ClarifyingQuestionOutput, StepRecord
from app.agent.verifier import VerifiedCitation
from app.api.schemas import (
    ChatAnswerResponse,
    ChatCitation,
    ChatClarifyResponse,
    DebugBlock,
    DebugStep,
    UsageSummary,
)
from app.providers import ProviderError
from app.services.cost import compute_call_cost_usd
from app.services.disclaimer import Language, disclaimer_for


def wrap(
    result: AgentResult,
    *,
    language: Language,
    conversation_id: str,
    question_id: str,
    user_question: str,
    retriever_name: str,
    verifier_name: str,
    prior_conversation_cost_usd: float = 0.0,
) -> tuple[ChatAnswerResponse | ChatClarifyResponse, dict[str, Any]]:
    """Wrap one agent turn into the wire response + the audit summary.

    ``prior_conversation_cost_usd`` is the sum of LLM-call costs already
    persisted for ``conversation_id`` before this question. Pass 0.0 for
    a new conversation. ``user_question`` is the verbatim text the user
    sent — persisted in the audit summary so the conversation list
    endpoint can render a title without re-running the agent.
    """
    debug_steps = [_step_to_debug(s, retriever_name, verifier_name) for s in result.steps]
    question_cost = round(sum(d.cost_usd or 0.0 for d in debug_steps), 8)
    conversation_cost = round(prior_conversation_cost_usd + question_cost, 8)
    verifier_passed = _all_verifiers_passed(result.steps)

    usage_summary = UsageSummary(
        question_total_cost_usd=question_cost,
        conversation_total_cost_usd=conversation_cost,
        step_count=len(debug_steps),
    )
    debug = DebugBlock(
        tool_calls=[d for d in debug_steps if d.kind == "tool_call"],
        verification_passed=verifier_passed,
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
        citations = [_verified_to_chat(vc) for vc in (result.verified_citations or [])]
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
        verifier_name=verifier_name,
        verifier_passed=verifier_passed,
    )
    return response, summary


def _verified_to_chat(vc: VerifiedCitation) -> ChatCitation:
    heading = vc.heading_path[-1] if vc.heading_path else ""
    return ChatCitation(
        passage_id=vc.passage_id,
        document=f"{vc.document_id}.md",
        document_updated=vc.document_updated,
        heading=heading,
        heading_path=list(vc.heading_path),
        quote=vc.quote,
    )


def _step_to_debug(step: StepRecord, retriever_name: str, verifier_name: str) -> DebugStep:
    name, detail = _name_and_detail(step, retriever_name, verifier_name)
    cost_usd: float | None = None
    if step.kind == "llm_call" and step.usage is not None:
        # Cost is a derived metric — an unpriced model (e.g. `stub-llm`
        # in CI fixtures, or a brand-new model not yet in the vendored
        # price table) shouldn't break the response. Surface as `None`.
        try:
            cost_usd = compute_call_cost_usd(step.usage)
        except ProviderError:
            cost_usd = None
    return DebugStep(
        step_id=step.step_id,
        kind=step.kind,
        name=name,
        detail=detail,
        duration_ms=0,
        usage=step.usage,
        cost_usd=cost_usd,
    )


def _name_and_detail(step: StepRecord, retriever_name: str, verifier_name: str) -> tuple[str, str]:
    if step.kind == "llm_call":
        stage = step.payload.get("stage", "agent_loop")
        finish = step.payload.get("finish_reason", "stop")
        tool_calls = step.payload.get("tool_calls") or []
        return f"agent.{stage}", f"finish_reason={finish} tool_calls={len(tool_calls)}"
    if step.kind == "tool_call":
        name = step.tool_name or "tool"
        if name == "search_convictions":
            args = step.payload.get("arguments") or {}
            query = args.get("query", "")
            k = args.get("k", "")
            via = f" via {retriever_name}" if retriever_name else ""
            return name, f"query={query!r} k={k}{via}"
        args = step.payload.get("arguments") or {}
        return name, "args=" + ",".join(f"{k}={v}" for k, v in args.items())
    if step.kind == "verifier":
        attempt = step.payload.get("attempt", 0)
        all_passed = step.payload.get("all_passed", False)
        verified = step.payload.get("verified") or []
        failures = step.payload.get("failures") or []
        return (
            verifier_name or "verifier",
            f"attempt={attempt} all_passed={all_passed} "
            f"verified={len(verified)} failures={len(failures)}",
        )
    return step.kind, ""


def _all_verifiers_passed(steps: list[StepRecord]) -> bool:
    """``true`` iff every verifier step passed (or there were none)."""
    verifier_steps = [s for s in steps if s.kind == "verifier"]
    if not verifier_steps:
        return True
    # The final verifier step is what counts — earlier failed attempts
    # are part of the retry path, not the steady-state outcome.
    return bool(verifier_steps[-1].payload.get("all_passed", False))


def _audit_summary(
    *,
    result: AgentResult,
    language: Language,
    user_question: str,
    retriever_name: str,
    verifier_name: str,
    verifier_passed: bool,
) -> dict[str, Any]:
    output = result.output
    summary: dict[str, Any] = {
        "language": language,
        "user_question": user_question,
        "rewritten_question": result.rewritten_question,
        "tool_call_count": result.tool_call_count,
        "search_count": result.search_count,
        "verifier_passed": verifier_passed,
        "retriever": retriever_name,
        "verifier_strategy": verifier_name,
        "step_count": len(result.steps),
        "step_kinds": [s.kind for s in result.steps],
        "output": output.model_dump(mode="json"),
        # Enriched citation provenance — lets the conversation-load
        # endpoint render the same chips as the live response.
        "verified_citations": [
            vc.model_dump(mode="json") for vc in (result.verified_citations or [])
        ],
    }
    if isinstance(output, AnswerOutput):
        summary["out_of_scope"] = output.out_of_scope
        summary["general_knowledge_used"] = output.general_knowledge_used
    return summary


__all__ = ["wrap"]
