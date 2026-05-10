"""Bounded tool-using agent loop with structured output.

The architecture (``docs/ARCHITECTURES.md`` § "Loop bounds") commits to:

- **Max 5 tool calls per question.** A 6th call is rejected before
  execution; the loop forces a final structured answer instead.
- **At least one ``search_convictions`` call before any AnswerOutput.**
  An AnswerOutput emitted before any search is rejected; the loop
  appends a system reminder and continues.
- **Schema attached every turn** (Pattern A). Each LLM call advertises
  both ``tools`` and the agent output schema. The model returns either
  ``tool_calls`` or ``parsed`` per turn — never both at once with the
  OpenAI adapter (``app/providers/openai.py`` enforces this).
- **No prior assistant text in the loop.** History is consumed only by
  the rewrite stage; the loop sees ``[system, user(rewritten)]``
  initially. This is the conversation-memory quarantine.

The verifier and retry-once-with-feedback path are **not** wired here
— they land in B8, which retrofits this module.
"""

import asyncio
import json
import uuid
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, TypeAdapter, ValidationError

from app.agent.rewrite import rewrite_question
from app.agent.schemas import (
    AGENT_OUTPUT_SCHEMA,
    AgentOutput,
    AgentResult,
    AnswerOutput,
    ConversationTurn,
    StepRecord,
)
from app.config import settings
from app.errors import AgentError, DomainError
from app.providers import LLMProvider, LLMResponse, Message, ToolCall
from app.tools import TOOLS, ToolContext

SYSTEM_PROMPT: str = (Path(__file__).parent / "prompts" / "system.md").read_text(encoding="utf-8")

_AGENT_OUTPUT_ADAPTER: TypeAdapter[AgentOutput] = TypeAdapter(AgentOutput)


async def run(
    user_message: str,
    history: list[ConversationTurn],
    *,
    tool_ctx: ToolContext,
    llm: LLMProvider,
) -> AgentResult:
    """Run one full agent turn.

    On the first turn (empty history) the rewrite stage is skipped and
    the agent loop sees ``user_message`` verbatim. On turn 2+ the
    rewrite stage produces a self-contained question.
    """
    steps: list[StepRecord] = []
    rewritten_question: str | None = None

    if history:
        rewritten, rewrite_step = await rewrite_question(user_message, history, llm=llm)
        steps.append(rewrite_step)
        loop_input = rewritten
        rewritten_question = rewritten
    else:
        loop_input = user_message

    output, loop_steps, tool_count, search_count = await _agent_loop(
        loop_input, tool_ctx=tool_ctx, llm=llm
    )
    steps.extend(loop_steps)

    return AgentResult(
        output=output,
        rewritten_question=rewritten_question,
        steps=steps,
        tool_call_count=tool_count,
        search_count=search_count,
    )


async def _agent_loop(
    question: str,
    *,
    tool_ctx: ToolContext,
    llm: LLMProvider,
) -> tuple[AgentOutput, list[StepRecord], int, int]:
    # All loop bounds are read from settings at call time so .env overrides
    # apply without restarting tests; see app/config/settings.py.
    max_tool_calls = settings.agent_max_tool_calls
    max_iterations = settings.agent_max_iterations

    messages: list[Message] = [
        Message(role="system", content=SYSTEM_PROMPT),
        Message(role="user", content=question),
    ]
    tool_definitions = [entry.definition for entry in TOOLS.values()]
    steps: list[StepRecord] = []
    tool_call_count = 0  # invariant: equals the number of *executed* tool calls
    search_count = 0
    budget_exhausted = False

    for _ in range(max_iterations):
        force_final = budget_exhausted or tool_call_count >= max_tool_calls

        response = await llm.generate(
            messages,
            tools=None if force_final else tool_definitions,
            schema=AGENT_OUTPUT_SCHEMA,
            reasoning_effort=settings.agent_reasoning_effort,
            max_output_tokens=settings.agent_max_output_tokens,
        )
        steps.append(_record_llm_call(response, stage="agent_loop"))

        # ---- Branch 1: model wants to call tools -----------------
        if response.tool_calls and not force_final:
            # Strict cap — never execute a call past the budget. If the
            # response would push us over, refuse all tool calls in this
            # batch and force a final answer next iteration. tool_call_count
            # remains at the executed count; budget_exhausted is the sentinel.
            if tool_call_count + len(response.tool_calls) > max_tool_calls:
                messages.append(_assistant_message(response))
                budget_msg = (
                    f"Tool budget exhausted ({max_tool_calls} calls max). Produce a "
                    "final structured answer using the evidence already gathered."
                )
                for tc in response.tool_calls:
                    messages.append(Message(role="tool", tool_call_id=tc.id, content=budget_msg))
                budget_exhausted = True
                continue

            messages.append(_assistant_message(response))
            results = await asyncio.gather(
                *[_execute_tool(tc, tool_ctx) for tc in response.tool_calls]
            )
            for tc, result_text in zip(response.tool_calls, results, strict=True):
                messages.append(Message(role="tool", tool_call_id=tc.id, content=result_text))
                steps.append(_record_tool_call(tc, result_text))

            tool_call_count += len(response.tool_calls)
            search_count += sum(1 for tc in response.tool_calls if tc.name == "search_convictions")
            continue

        # ---- Branch 2: model produced structured output -----------
        if response.parsed is not None:
            try:
                output = _AGENT_OUTPUT_ADAPTER.validate_python(response.parsed)
            except ValidationError as exc:
                raise AgentError(f"model output failed schema validation: {exc}") from exc

            # Lower-bound enforcement — only AnswerOutput requires a
            # prior search. ClarifyingQuestionOutput is always allowed
            # (it's not "a final answer").
            if isinstance(output, AnswerOutput) and search_count == 0:
                content = response.content or json.dumps(response.parsed)
                messages.append(Message(role="assistant", content=content))
                messages.append(
                    Message(
                        role="user",
                        content=(
                            "You must call search_convictions to gather evidence "
                            "before producing an answer. Use the tools."
                        ),
                    )
                )
                continue

            return output, steps, tool_call_count, search_count

        # Defensive — schema attached but neither tool_calls nor parsed.
        # Strict mode should make this unreachable.
        raise AgentError("model returned neither tool_calls nor parsed output")

    raise AgentError(f"agent loop exceeded {max_iterations} iterations")


# --- helpers --------------------------------------------------------------


async def _execute_tool(call: ToolCall, ctx: ToolContext) -> str:
    """Dispatch one tool call; return JSON-stringified result or error.

    Domain errors raised by tools are caught and returned as a string
    the model can act on (typically by retrying with corrected
    arguments). Non-domain exceptions propagate.
    """
    entry = TOOLS.get(call.name)
    if entry is None:
        available = ", ".join(sorted(TOOLS.keys()))
        return _error_payload(f"Tool {call.name!r} does not exist. Available tools: {available}")

    try:
        result = await entry.func(ctx, **call.arguments)
    except TypeError as exc:
        return _error_payload(f"Tool {call.name!r} called with bad arguments: {exc}")
    except DomainError as exc:
        return _error_payload(f"{type(exc).__name__}: {exc}")

    return _serialize_result(result)


def _serialize_result(result: Any) -> str:
    if isinstance(result, BaseModel):
        return result.model_dump_json()
    if isinstance(result, list):
        return json.dumps([_to_jsonable(item) for item in result], default=_default_jsonable)
    return json.dumps(_to_jsonable(result), default=_default_jsonable)


def _to_jsonable(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    return value


def _default_jsonable(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, date):
        return value.isoformat()
    raise TypeError(f"object of type {type(value).__name__} is not JSON serializable")


def _error_payload(message: str) -> str:
    return json.dumps({"error": message})


def _assistant_message(response: LLMResponse) -> Message:
    return Message(
        role="assistant",
        content=response.content,
        tool_calls=list(response.tool_calls),
    )


def _record_llm_call(response: LLMResponse, *, stage: str) -> StepRecord:
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


def _record_tool_call(call: ToolCall, result_text: str) -> StepRecord:
    payload: dict[str, Any] = {
        "tool_call_id": call.id,
        "arguments": call.arguments,
        "result": _maybe_parse_json(result_text),
    }
    return StepRecord(
        step_id=str(uuid.uuid4()),
        kind="tool_call",
        timestamp=datetime.now(UTC),
        payload=payload,
        tool_name=call.name,
    )


def _maybe_parse_json(text: str) -> Any:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


__all__ = ["SYSTEM_PROMPT", "run"]
