"""Step-record builders + the resolver-side fetch adapter.

Three record builders, one per :class:`StepRecord` kind, plus a thin
adapter (:func:`resolve_output`) that fetches passages from the repo
and hands them to the pure offset resolver.

The adapter lives here (not under :mod:`app.agent.resolver`) because
the pure resolver owns no I/O — :func:`app.agent.resolver.resolve_answer`
takes a passages dict it does not load.
"""

import json
import uuid
from datetime import UTC, datetime
from typing import Any

from app.agent.resolver import OffsetResolution, resolve_answer
from app.agent.schemas import AnswerOutput, StepRecord
from app.agent.tools import ToolContext
from app.errors import VerificationError
from app.providers import LLMResponse, ToolCall
from app.repositories import passages as passages_repo
from app.schemas.passage import Passage


def record_llm_call(response: LLMResponse, *, stage: str, duration_ms: int = 0) -> StepRecord:
    payload: dict[str, Any] = {
        "stage": stage,
        "finish_reason": response.finish_reason,
        "tool_calls": [tc.model_dump(mode="json") for tc in response.tool_calls],
    }
    if response.parsed is not None:
        payload["parsed"] = response.parsed
    if response.content is not None and response.parsed is None:
        payload["content"] = response.content
    return StepRecord(
        step_id=str(uuid.uuid4()),
        kind="llm_call",
        timestamp=datetime.now(UTC),
        payload=payload,
        usage=response.usage,
        duration_ms=duration_ms,
    )


def record_tool_call(call: ToolCall, result_text: str, *, duration_ms: int = 0) -> StepRecord:
    return StepRecord(
        step_id=str(uuid.uuid4()),
        kind="tool_call",
        timestamp=datetime.now(UTC),
        payload={
            "tool_call_id": call.id,
            "arguments": call.arguments,
            "result": _maybe_parse_json(result_text),
        },
        tool_name=call.name,
        duration_ms=duration_ms,
    )


def record_resolver(resolution: OffsetResolution, *, duration_ms: int = 0) -> StepRecord:
    return StepRecord(
        step_id=str(uuid.uuid4()),
        kind="resolver",
        timestamp=datetime.now(UTC),
        payload={
            "entries": [e.model_dump(mode="json") for e in resolution.entries],
        },
        duration_ms=duration_ms,
    )


async def resolve_output(output: AnswerOutput, *, ctx: ToolContext) -> OffsetResolution:
    """Fetch each cited passage and run the offset resolver.

    Each unique ``passage_id`` in ``output.citations`` is loaded via the
    passage repository. ``None`` results (passage_id not in the store)
    are passed through to :func:`resolve_answer` as a missing key, which
    records a ``passage_not_found`` failure for that citation. Repository
    errors propagate as :class:`VerificationError`.
    """
    unique_ids = {c.passage_id for c in output.citations}
    passages: dict[str, Passage] = {}
    try:
        for pid in unique_ids:
            passage = await passages_repo.get(ctx.session, pid)
            if passage is not None:
                passages[pid] = passage
    except Exception as exc:  # repo errors are bug-class for the resolver
        raise VerificationError(f"failed to load passages for resolution: {exc}") from exc
    return resolve_answer(output, passages)


def _maybe_parse_json(text: str) -> Any:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


__all__ = [
    "record_llm_call",
    "record_resolver",
    "record_tool_call",
    "resolve_output",
]
