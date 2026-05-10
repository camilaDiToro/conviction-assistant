"""Step-record builders + the verifier-side fetch adapter.

Three record builders, one per :class:`StepRecord` kind, plus a thin
adapter (:func:`verify_output`) that fetches passages from the repo and
hands them to the pure verifier. B9 will reuse these to populate the
``audit_log`` table.

The adapter lives here (not under :mod:`app.verifier`) because the pure
verifier owns no I/O — see :file:`docs/b8-decisions.md` § "Why
``app/verifier/`` is its own layer".
"""

import json
import uuid
from datetime import UTC, datetime
from typing import Any

from app.agent.schemas import AnswerOutput, StepRecord
from app.agent.tools import ToolContext
from app.agent.verifier import VerificationResult
from app.errors import VerificationError
from app.providers import LLMResponse, ToolCall
from app.repositories import passages as passages_repo
from app.schemas.passage import Passage


def record_llm_call(response: LLMResponse, *, stage: str) -> StepRecord:
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
    )


def record_tool_call(call: ToolCall, result_text: str) -> StepRecord:
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
    )


def record_verifier(result: VerificationResult, *, attempt: int) -> StepRecord:
    return StepRecord(
        step_id=str(uuid.uuid4()),
        kind="verifier",
        timestamp=datetime.now(UTC),
        payload={
            "attempt": attempt,
            "all_passed": result.all_passed,
            "verified": [vc.model_dump(mode="json") for vc in result.verified],
            "failures": [f.model_dump(mode="json") for f in result.failures],
        },
    )


async def verify_output(output: AnswerOutput, *, ctx: ToolContext) -> VerificationResult:
    """Fetch each cited passage and run the configured verifier.

    Each unique ``passage_id`` in ``output.citations`` is loaded via the
    passage repository. ``None`` results (passage_id not in the store)
    are passed through to the verifier as a missing key, which records a
    ``passage_not_found`` failure for that citation. Repository errors
    propagate as :class:`VerificationError`. The verifier itself comes
    from ``ctx.verifier`` — :class:`SubstringVerifier` by default.
    """
    unique_ids = {c.passage_id for c in output.citations}
    passages: dict[str, Passage] = {}
    try:
        for pid in unique_ids:
            passage = await passages_repo.get(ctx.session, pid)
            if passage is not None:
                passages[pid] = passage
    except Exception as exc:  # repo errors are bug-class for the verifier
        raise VerificationError(f"failed to load passages for verification: {exc}") from exc
    return ctx.verifier.verify(output, passages)


def _maybe_parse_json(text: str) -> Any:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


__all__ = [
    "record_llm_call",
    "record_tool_call",
    "record_verifier",
    "verify_output",
]
