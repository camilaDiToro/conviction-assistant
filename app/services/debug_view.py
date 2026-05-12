"""Debug-drawer view formatting for the chat trace.

Two paths feed the same drawer:

- **Live**: the chat handler emits ``StepRecord``s during the agent loop;
  :func:`step_to_debug` formats each one for the wire and
  :func:`response_debug_step` synthesizes a final ``kind='response'``
  step so the model's answer shows inline with the rest.
- **Historical**: when the user reloads a conversation from the sidebar,
  :func:`reconstruct_steps_from_audit` rebuilds ``StepRecord``s from
  persisted ``audit_log`` rows and reuses the same formatting helpers
  so the drawer renders identically.

Kept separate from :mod:`app.services.wrap_response` because formatting
for the debug drawer is a distinct concern from the
``AgentResult → wire response`` mapping.
"""

import json
import uuid
from datetime import datetime
from typing import Any

from app.agent import StepRecord
from app.api.schemas import DebugStep
from app.providers import TokenUsage
from app.repositories import audit as audit_repo


def step_to_debug(step: StepRecord, retriever_name: str) -> DebugStep:
    name, detail = _name_and_detail(step, retriever_name)
    return DebugStep(
        step_id=step.step_id,
        kind=step.kind,
        name=name,
        detail=detail,
        duration_ms=step.duration_ms,
        usage=step.usage,
        result=_step_result_summary(step),
    )


def response_debug_step(
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
        step_id=step_id or str(uuid.uuid4()),
        kind="response",
        name=f"response.{kind}",
        detail=detail,
        duration_ms=0,
        usage=None,
        result=result,
    )


def reconstruct_steps_from_audit(
    rows: list[audit_repo.AuditRow],
    *,
    retriever_name: str,
) -> list[DebugStep]:
    """Rebuild ``DebugStep``s from persisted audit rows.

    The live request emits ``StepRecord``s through :func:`step_to_debug`.
    Historical requests are read back as :class:`audit_repo.AuditRow` —
    this function deserializes the JSON columns into a transient
    :class:`StepRecord` and reuses the same name/detail logic so the
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
        tool_name = payload.pop("tool_name", None)
        duration_ms_raw = payload.pop("duration_ms", 0)
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
    return [step_to_debug(s, retriever_name) for s in transient]


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
            f"entries={len(entries)} anchored={anchored} unresolved={len(entries) - anchored}",
        )
    return step.kind, ""


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


def _truncate(s: str, n: int) -> str:
    s = s.replace("\n", " ").strip()
    return s if len(s) <= n else s[: n - 1] + "…"


__all__ = ["reconstruct_steps_from_audit", "response_debug_step", "step_to_debug"]
