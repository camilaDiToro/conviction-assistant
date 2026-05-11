"""Admin conversation review services.

Pure transforms over audit rows:

- :func:`build_trace` groups rows by ``question_id`` and emits the
  per-question summary used by ``GET /admin/conversations/{id}``.

The router does the DB fetch and 404, then calls these; this module owns
the grouping/aggregation logic that previously lived in the router.
"""

import json
from collections import defaultdict
from datetime import datetime
from typing import Any, cast

from app.api.schemas import (
    ConversationQuestionSummary,
    ConversationTraceResponse,
)
from app.repositories import audit as audit_repo


def build_trace(
    conversation_id: str, rows: list[audit_repo.AuditRow]
) -> ConversationTraceResponse:
    by_question: dict[str, list[audit_repo.AuditRow]] = defaultdict(list)
    for row in rows:
        by_question[row["question_id"]].append(row)

    question_ids = sorted(by_question, key=lambda qid: by_question[qid][0]["timestamp"])

    questions: list[ConversationQuestionSummary] = []
    for qid in question_ids:
        question_rows = by_question[qid]
        response_row = _find_response_row(question_rows)
        if response_row is None:
            # Partial write or in-flight question — skip rather than fabricate.
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
                step_count=len(non_response_rows),
                step_kinds=[r["kind"] for r in non_response_rows],
                retriever=summary_payload.get("retriever", ""),
            )
        )

    return ConversationTraceResponse(
        conversation_id=conversation_id,
        questions=questions,
        step_count_total=len(rows),
    )


def _find_response_row(
    rows: list[audit_repo.AuditRow],
) -> audit_repo.AuditRow | None:
    for row in rows:
        if row["kind"] == "response":
            return row
    return None


__all__ = ["build_trace"]
