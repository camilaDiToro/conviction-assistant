"""Pure mapping: ``AgentResult`` → wire ``ChatResponse`` + audit summary.

This service has no side effects. Given the agent's structured result and
the request-level identifiers, it produces:

1. The wire response (``ChatAnswerResponse`` or ``ChatClarifyResponse``)
   the HTTP handler returns to the client.
2. A summary dict the caller stores as the ``kind='response'`` audit row.

Citation enrichment uses the ``CitationResolution`` entries the agent
already produced — no extra DB hits at response time. Cost is computed
per LLM-call step via :func:`app.services.cost.compute_call_cost_usd`.
"""

import json
from datetime import datetime
from typing import Any

from app.agent import AgentResult, AnswerOutput, ClarifyingQuestionOutput, StepRecord
from app.agent.resolver import CitationResolution
from app.api.schemas import (
    ChatAnswerResponse,
    ChatCitation,
    ChatClarifyResponse,
    DebugBlock,
    DebugStep,
    UsageSummary,
)
from app.providers import ProviderError, TokenUsage
from app.repositories import audit as audit_repo
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
    prior_conversation_cost_usd: float = 0.0,
) -> tuple[ChatAnswerResponse | ChatClarifyResponse, dict[str, Any]]:
    """Wrap one agent turn into the wire response + the audit summary.

    ``prior_conversation_cost_usd`` is the sum of LLM-call costs already
    persisted for ``conversation_id`` before this question. Pass 0.0 for
    a new conversation. ``user_question`` is the verbatim text the user
    sent — persisted in the audit summary so the conversation list
    endpoint can render a title without re-running the agent.
    """
    resolution_entries = list(result.resolution.entries) if result.resolution else []
    debug_steps = [_step_to_debug(s, retriever_name) for s in result.steps]
    question_cost = round(sum(d.cost_usd or 0.0 for d in debug_steps), 8)
    conversation_cost = round(prior_conversation_cost_usd + question_cost, 8)

    debug_steps.append(
        _response_debug_step(
            result.output.model_dump(mode="json"),
            resolution_entries=[e.model_dump(mode="json") for e in resolution_entries],
        )
    )

    usage_summary = UsageSummary(
        question_total_cost_usd=question_cost,
        conversation_total_cost_usd=conversation_cost,
        step_count=len(debug_steps),
        duration_ms=_question_duration_ms(result.steps),
    )
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
        document_updated=entry.document_updated,
        heading=heading,
        heading_path=list(entry.heading_path),
        passage_text=entry.passage_text,
        start=entry.start,
        end=entry.end,
    )


def _step_to_debug(step: StepRecord, retriever_name: str) -> DebugStep:
    name, detail = _name_and_detail(step, retriever_name)
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
        duration_ms=step.duration_ms,
        usage=step.usage,
        cost_usd=cost_usd,
        result=_step_result_summary(step),
    )


def _step_result_summary(step: StepRecord) -> dict[str, Any] | None:
    """Step-kind-specific JSON summary of what the step produced.

    Surfaces the data the audit_log already persists (tool return values,
    LLM parsed output, resolver entries) so the debug drawer can show
    *what came back*, not just *what was called*.
    """
    p = step.payload or {}
    if step.kind == "tool_call":
        result = p.get("result")
        return {"result": result} if result is not None else None
    if step.kind == "llm_call":
        out: dict[str, Any] = {}
        tool_calls = p.get("tool_calls") or []
        if tool_calls:
            out["tool_calls"] = tool_calls
        if p.get("parsed") is not None:
            out["parsed"] = p["parsed"]
        if p.get("content") is not None:
            out["content"] = p["content"]
        return out or None
    if step.kind == "resolver":
        return {"entries": p.get("entries") or []}
    return None


def _response_debug_step(
    output_dump: dict[str, Any],
    *,
    resolution_entries: list[dict[str, Any]] | None = None,
    step_id: str | None = None,
) -> DebugStep:
    """Synthetic ``kind='response'`` step appended at the end of the trace.

    Lets the debug drawer show the model's final answer (or clarifying
    question) inline with the rest of the steps, instead of forcing the
    reviewer to look at the message bubble for the text and the drawer
    for everything else.
    """
    import uuid as _uuid

    kind = output_dump.get("kind", "answer")
    if kind == "clarifying_question":
        question = output_dump.get("question", "")
        detail = f"clarifying_question: {_truncate(question, 80)}"
    else:
        answer = output_dump.get("answer", "")
        detail = f"answer ({len(answer)} chars): {_truncate(answer, 80)}"
    result: dict[str, Any] = {"output": output_dump}
    if resolution_entries:
        result["resolution_entries"] = resolution_entries
    return DebugStep(
        step_id=step_id or str(_uuid.uuid4()),
        kind="response",
        name=f"response.{kind}",
        detail=detail,
        duration_ms=0,
        usage=None,
        cost_usd=None,
        result=result,
    )


def _truncate(s: str, n: int) -> str:
    s = s.replace("\n", " ").strip()
    return s if len(s) <= n else s[: n - 1] + "…"


def _name_and_detail(step: StepRecord, retriever_name: str) -> tuple[str, str]:
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
    if step.kind == "resolver":
        entries = step.payload.get("entries") or []
        anchored = sum(1 for e in entries if e.get("failure_reason") is None)
        return (
            "resolver",
            f"entries={len(entries)} anchored={anchored} "
            f"unresolved={len(entries) - anchored}",
        )
    return step.kind, ""


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


def reconstruct_steps_from_audit(
    rows: list[audit_repo.AuditRow],
    *,
    retriever_name: str,
) -> list[DebugStep]:
    """Rebuild ``DebugStep``s from persisted audit rows.

    The live request emits ``StepRecord``s through :func:`_step_to_debug`.
    Historical requests are read back as :class:`audit_repo.AuditRow` —
    this function deserializes the JSON columns into a transient
    :class:`StepRecord` and reuses the same name/detail/cost logic so the
    historical drawer renders identically to the live one.

    Rows whose ``kind`` is not in the current literal (e.g. legacy
    ``'verifier'`` rows from before the offset-resolver rollout) are
    skipped — the response row is expected to be filtered out by the
    caller, but defending here makes the function safe regardless.
    """
    transient: list[StepRecord] = []
    for row in rows:
        kind = row["kind"]
        if kind not in ("llm_call", "tool_call", "resolver"):
            continue
        try:
            payload = json.loads(row["payload"]) if row["payload"] else {}
        except (ValueError, TypeError):
            payload = {}
        if not isinstance(payload, dict):
            payload = {}
        tool_name = payload.pop("tool_name", None) if isinstance(payload, dict) else None
        duration_ms_raw = payload.pop("duration_ms", 0) if isinstance(payload, dict) else 0
        try:
            duration_ms = int(duration_ms_raw)
        except (TypeError, ValueError):
            duration_ms = 0
        usage: TokenUsage | None = None
        if row["usage"]:
            try:
                usage = TokenUsage.model_validate(json.loads(row["usage"]))
            except (ValueError, TypeError):
                usage = None
        try:
            ts = datetime.fromisoformat(row["timestamp"])
        except ValueError:
            ts = datetime.fromtimestamp(0)
        transient.append(
            StepRecord(
                step_id=row["step_id"],
                kind=kind,  # type: ignore[arg-type]
                timestamp=ts,
                payload=payload,
                usage=usage,
                tool_name=tool_name if isinstance(tool_name, str) else None,
                duration_ms=duration_ms,
            )
        )
    return [_step_to_debug(s, retriever_name) for s in transient]


def build_response_debug_step(
    output_dump: dict[str, Any],
    *,
    resolution_entries: list[dict[str, Any]] | None = None,
    step_id: str | None = None,
) -> DebugStep:
    """Public wrapper for :func:`_response_debug_step` so the historical
    steps endpoint can append the same synthetic response step the live
    path emits.
    """
    return _response_debug_step(
        output_dump, resolution_entries=resolution_entries, step_id=step_id
    )


__all__ = ["build_response_debug_step", "reconstruct_steps_from_audit", "wrap"]
