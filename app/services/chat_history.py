"""Reconstruction of user-facing chat history from ``audit_log`` rows.

The live ``/chat`` path produces a wire response straight from
``AgentResult`` (see :mod:`app.services.wrap_response`). When the user
reloads a historical conversation from the sidebar, the same wire shapes
are rebuilt here from the persisted ``audit_log`` rows.

Three responsibilities:

- map a ``kind='response'`` payload to a ``ConversationMessage``;
- map a stored ``CitationResolution`` dump to a ``ChatCitation``;
- summarize token usage and wall-clock duration for a per-question
  debug trace.
"""

import json
from datetime import datetime
from typing import Any, cast

from app.api.schemas import (
    ChatCitation,
    ConversationAnswerMessage,
    ConversationClarifyMessage,
    ConversationListItem,
    ConversationMessage,
    DebugStep,
    QuestionStepsResponse,
    UsageSummary,
)
from app.providers.text_repair import repair_broken_unicode_escapes
from app.repositories import audit as audit_repo
from app.services.debug_view import reconstruct_steps_from_audit, response_debug_step

_TITLE_MAX = 120


def list_item_from_summary_row(row: audit_repo.ConversationSummaryRow) -> ConversationListItem:
    """Map one ``list_conversation_summaries`` row to the wire item."""
    try:
        payload = cast(dict[str, Any], json.loads(row["first_payload"]))
    except (ValueError, TypeError):
        payload = {}
    title = make_title(payload.get("user_question") or payload.get("rewritten_question") or "")
    return ConversationListItem(
        conversation_id=row["conversation_id"],
        title=title,
        first_ts=datetime.fromisoformat(row["first_ts"]),
        last_ts=datetime.fromisoformat(row["last_ts"]),
        question_count=row["question_count"],
    )


def message_from_response_row(row: audit_repo.AuditRow) -> ConversationMessage | None:
    """Reconstruct one ``ConversationMessage`` from a ``kind='response'``
    row. Returns ``None`` if the row payload won't parse as JSON."""
    try:
        payload = cast(dict[str, Any], json.loads(row["payload"]))
    except (ValueError, TypeError):
        return None
    return _message_from_payload(row, payload)


def audit_duration_ms(rows: list[audit_repo.AuditRow]) -> int:
    """Wall-clock span between first and last audit row for a question."""
    if not rows:
        return 0
    parsed: list[datetime] = []
    for r in rows:
        try:
            parsed.append(datetime.fromisoformat(r["timestamp"]))
        except (ValueError, TypeError):
            continue
    if not parsed:
        return 0
    delta = max(parsed) - min(parsed)
    return int(delta.total_seconds() * 1000)


def steps_response_from_rows(
    response_row: audit_repo.AuditRow,
    step_rows: list[audit_repo.AuditRow],
    *,
    conversation_id: str,
    question_id: str,
) -> QuestionStepsResponse:
    """Assemble the per-question debug trace from persisted audit rows.

    Mirrors the live ``/chat`` path's ``debug.steps``: tool/llm/resolver
    steps reconstructed from ``step_rows`` plus a synthetic ``response``
    step rebuilt from the ``kind='response'`` payload.
    """
    try:
        summary = cast(dict[str, Any], json.loads(response_row["payload"]))
    except (ValueError, TypeError):
        summary = {}
    retriever_name = str(summary.get("retriever") or "")

    steps = reconstruct_steps_from_audit(step_rows, retriever_name=retriever_name)

    output_dump = summary.get("output") if isinstance(summary.get("output"), dict) else None
    if output_dump is not None:
        resolution_entries = summary.get("resolution_entries")
        if not isinstance(resolution_entries, list):
            resolution_entries = None
        steps.append(
            response_debug_step(
                output_dump,
                resolution_entries=resolution_entries,
                step_id=response_row["step_id"],
            )
        )

    return QuestionStepsResponse(
        conversation_id=conversation_id,
        question_id=question_id,
        steps=steps,
        usage_summary=usage_summary_from_steps(steps, duration_ms=audit_duration_ms(step_rows)),
    )


def usage_summary_from_steps(steps: list[DebugStep], *, duration_ms: int) -> UsageSummary:
    """Aggregate ``TokenUsage`` from llm_call debug steps. Mirrors the
    live-path ``UsageSummary`` shape produced by
    :mod:`app.services.wrap_response` so the historical drawer renders
    identical totals."""
    usages = [s.usage for s in steps if s.kind == "llm_call" and s.usage is not None]
    return UsageSummary(
        llm_call_count=len(usages),
        prompt_tokens=sum(u.prompt_tokens for u in usages),
        completion_tokens=sum(u.completion_tokens for u in usages),
        cached_tokens=sum(u.cached_tokens for u in usages),
        reasoning_tokens=sum(u.reasoning_tokens for u in usages),
        step_count=len(steps),
        duration_ms=duration_ms,
    )


def make_title(text: str) -> str:
    text = text.strip().replace("\n", " ")
    if not text:
        return "(untitled)"
    return text if len(text) <= _TITLE_MAX else text[: _TITLE_MAX - 1] + "…"


def _message_from_payload(row: audit_repo.AuditRow, payload: dict[str, Any]) -> ConversationMessage:
    output = payload.get("output") or {}
    kind = output.get("kind", "answer")

    user_question_raw = payload.get("user_question") or payload.get("rewritten_question") or ""
    common = {
        "question_id": row["question_id"],
        "timestamp": row["timestamp"],  # parsed by Pydantic
        "user_question": _repair(user_question_raw) or "",
        "language": payload.get("language", "en"),
    }

    if kind == "clarifying_question":
        return ConversationClarifyMessage(
            **common,
            clarifying_question=_repair(output.get("question")),
            clarifying_options=[
                repaired
                for o in (output.get("options") or [])
                if (repaired := _repair(o)) is not None
            ],
        )

    citations = [
        chat
        for entry in (payload.get("resolution_entries") or [])
        if (chat := _citation_from_dump(entry)) is not None
    ]
    return ConversationAnswerMessage(
        **common,
        answer=_repair(output.get("answer")),
        citations=citations,
        general_knowledge_used=output.get("general_knowledge_used"),
        general_knowledge_section=_repair(output.get("general_knowledge_section")),
        out_of_scope=output.get("out_of_scope"),
    )


def _citation_from_dump(dump: dict[str, Any]) -> ChatCitation | None:
    """Map a serialized ``CitationResolution`` payload to the wire shape.

    Entries whose passage couldn't be loaded (``passage_not_found``) are
    dropped — without ``passage_text`` there is nothing to show.
    """
    passage_text = dump.get("passage_text")
    document_id = dump.get("document_id")
    if not isinstance(passage_text, str) or not document_id:
        return None
    heading_path = list(dump.get("heading_path") or [])
    heading = heading_path[-1] if heading_path else ""
    start = dump.get("start")
    end = dump.get("end")
    return ChatCitation(
        passage_id=dump.get("passage_id", ""),
        document=f"{document_id}.md",
        heading=heading,
        heading_path=heading_path,
        passage_text=passage_text,
        start=int(start) if isinstance(start, int) else None,
        end=int(end) if isinstance(end, int) else None,
    )


def _repair(s: str | None) -> str | None:
    """Apply the broken-escape repair to historical text persisted before
    the OpenAI adapter started repairing on parse. Idempotent — strings
    that were stored cleanly are returned unchanged."""
    if s is None:
        return None
    return repair_broken_unicode_escapes(s)


__all__ = [
    "audit_duration_ms",
    "list_item_from_summary_row",
    "make_title",
    "message_from_response_row",
    "steps_response_from_rows",
    "usage_summary_from_steps",
]
