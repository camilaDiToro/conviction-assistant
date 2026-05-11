"""Bounded tool-using agent loop with structured output.

Architectural commitments (``docs/ARCHITECTURES.md`` § "Loop bounds"):

- **Max 5 tool calls per question.** A 6th call is rejected before
  execution; the loop forces a final structured answer instead.
- **At least one ``search_convictions`` call before any AnswerOutput.**
  An AnswerOutput emitted before any search is rejected; the loop
  appends a system reminder and continues.
- **Schema attached every turn** (Pattern A). Each LLM call advertises
  both ``tools`` and the agent output schema. The model returns either
  ``tool_calls`` or ``parsed`` per turn.
- **No prior assistant text in the loop.** History is consumed only by
  the rewrite stage; the loop sees ``[system, user(rewritten)]``
  initially. This is the conversation-memory quarantine.
- **Deterministic offset resolver.** Each ``AnswerOutput`` citation's
  quote is resolved to ``(start, end)`` offsets in the cited passage;
  the literal quote is dropped. Non-anchoring citations survive
  without offsets (the popup shows the passage with no highlight).

Helpers live in sibling modules: tool dispatch in :mod:`app.agent.tool_dispatch`,
step recorders + resolve adapter in :mod:`app.agent.audit`, dedupe in
:mod:`app.agent.dedupe`. Language detection is the rewrite stage's
responsibility (see :mod:`app.agent.rewrite`); the agent loop just
consumes the ``detected_language`` it returns.
"""

import asyncio
import json
from pathlib import Path
from time import perf_counter

from pydantic import TypeAdapter, ValidationError

from app.agent.audit import (
    record_llm_call,
    record_resolver,
    record_tool_call,
    resolve_output,
)
from app.agent.dedupe import dedupe_citations
from app.agent.resolver import OffsetResolution
from app.agent.rewrite import rewrite_question
from app.agent.schemas import (
    AGENT_OUTPUT_SCHEMA,
    AgentOutput,
    AgentResult,
    AnswerOutput,
    ConversationTurn,
    StepRecord,
)
from app.agent.tool_dispatch import execute_tool
from app.agent.tools import TOOLS, ToolContext
from app.config import settings
from app.errors import AgentError
from app.i18n import Language
from app.providers import LLMProvider, LLMResponse, Message
from app.providers.base import ToolCall, ToolDefinition

_LANGUAGE_NAME: dict[Language, str] = {
    "pt": "Portuguese",
    "es": "Spanish",
    "en": "English",
}

SYSTEM_PROMPT: str = (Path(__file__).parent / "prompts" / "system.md").read_text(encoding="utf-8")

_AGENT_OUTPUT_ADAPTER: TypeAdapter[AgentOutput] = TypeAdapter(AgentOutput)


async def run(
    user_message: str,
    history: list[ConversationTurn],
    *,
    tool_ctx: ToolContext,
    llm: LLMProvider,
) -> AgentResult:
    steps: list[StepRecord] = []

    rewritten, language, rewrite_step = await rewrite_question(user_message, history, llm=llm)
    steps.append(rewrite_step)
    loop_input = rewritten
    rewritten_question = rewritten if history else None

    output, loop_steps, tool_count, search_count, resolution = await _agent_loop(
        loop_input, tool_ctx=tool_ctx, llm=llm, language=language
    )
    steps.extend(loop_steps)

    return AgentResult(
        output=output,
        rewritten_question=rewritten_question,
        language=language,
        steps=steps,
        tool_call_count=tool_count,
        search_count=search_count,
        resolution=resolution,
    )


async def _agent_loop(
    question: str,
    *,
    tool_ctx: ToolContext,
    llm: LLMProvider,
    language: Language = "en",
) -> tuple[AgentOutput, list[StepRecord], int, int, OffsetResolution | None]:
    max_tool_calls = settings.agent_max_tool_calls
    max_iterations = settings.agent_max_iterations

    messages = _build_initial_messages(question, language)
    tool_definitions = [entry.definition for entry in TOOLS.values()]
    steps: list[StepRecord] = []
    tool_call_count = 0
    search_count = 0
    budget_exhausted = False

    for _ in range(max_iterations):
        force_final = budget_exhausted or tool_call_count >= max_tool_calls

        response, llm_step = await _llm_turn(llm, messages, tool_definitions, force_final)
        steps.append(llm_step)

        if response.tool_calls and not force_final:
            executed, searched, budget_exhausted, tool_steps = await _handle_tool_branch(
                response, messages, tool_ctx, tool_call_count, max_tool_calls
            )
            tool_call_count += executed
            search_count += searched
            steps.extend(tool_steps)
            continue

        if response.parsed is not None:
            output = _parse_output(response)

            if _needs_search_first(output, search_count):
                _append_search_reminder(messages, response)
                continue

            if isinstance(output, AnswerOutput):
                output, resolver_step, resolution = await _resolve_answer(output, tool_ctx)
                steps.append(resolver_step)
                return output, steps, tool_call_count, search_count, resolution

            return output, steps, tool_call_count, search_count, None

        raise AgentError("model returned neither tool_calls nor parsed output")

    raise AgentError(f"agent loop exceeded {max_iterations} iterations")


def _build_initial_messages(question: str, language: Language) -> list[Message]:
    lang_name = _LANGUAGE_NAME[language]
    language_directive = (
        f"ANSWER LANGUAGE: {lang_name} ({language}). "
        f"You MUST write the `answer` field and any clarifying `question` "
        f"in {lang_name}, regardless of the language of the cited passages. "
        f"Citation `quote` fields stay in their source language."
    )
    return [
        Message(role="system", content=SYSTEM_PROMPT),
        Message(role="system", content=language_directive),
        Message(role="user", content=question),
    ]


async def _llm_turn(
    llm: LLMProvider,
    messages: list[Message],
    tool_definitions: list[ToolDefinition],
    force_final: bool,
) -> tuple[LLMResponse, StepRecord]:
    t0 = perf_counter()
    response = await llm.generate(
        messages,
        tools=None if force_final else tool_definitions,
        schema=AGENT_OUTPUT_SCHEMA,
        reasoning_effort=settings.agent_reasoning_effort,
        max_output_tokens=settings.agent_max_output_tokens,
    )
    dur = int((perf_counter() - t0) * 1000)
    return response, record_llm_call(response, stage="agent_loop", duration_ms=dur)


async def _handle_tool_branch(
    response: LLMResponse,
    messages: list[Message],
    tool_ctx: ToolContext,
    tool_call_count: int,
    max_tool_calls: int,
) -> tuple[int, int, bool, list[StepRecord]]:
    """Execute the model's tool calls. Returns (executed, searched, budget_exhausted, steps)."""
    messages.append(_assistant_message(response))

    # Strict cap — never execute a call past the budget. If the response
    # would push us over, refuse every call in this batch and force a
    # final answer next iteration.
    if tool_call_count + len(response.tool_calls) > max_tool_calls:
        budget_msg = (
            f"Tool budget exhausted ({max_tool_calls} calls max). Produce a "
            "final structured answer using the evidence already gathered."
        )
        for tc in response.tool_calls:
            messages.append(Message(role="tool", tool_call_id=tc.id, content=budget_msg))
        return 0, 0, True, []

    async def _timed_exec(tc: ToolCall) -> tuple[str, int]:
        ts = perf_counter()
        text = await execute_tool(tc, tool_ctx)
        return text, int((perf_counter() - ts) * 1000)

    timed = await asyncio.gather(*[_timed_exec(tc) for tc in response.tool_calls])
    steps: list[StepRecord] = []
    for tc, (result_text, dur) in zip(response.tool_calls, timed, strict=True):
        messages.append(Message(role="tool", tool_call_id=tc.id, content=result_text))
        steps.append(record_tool_call(tc, result_text, duration_ms=dur))

    searched = sum(1 for tc in response.tool_calls if tc.name == "search_convictions")
    return len(response.tool_calls), searched, False, steps


def _parse_output(response: LLMResponse) -> AgentOutput:
    try:
        return _AGENT_OUTPUT_ADAPTER.validate_python(response.parsed)
    except ValidationError as exc:
        raise AgentError(f"model output failed schema validation: {exc}") from exc


def _needs_search_first(output: AgentOutput, search_count: int) -> bool:
    return isinstance(output, AnswerOutput) and search_count == 0 and not output.out_of_scope


def _append_search_reminder(messages: list[Message], response: LLMResponse) -> None:
    content = response.content or json.dumps(response.parsed)
    messages.append(Message(role="assistant", content=content))
    messages.append(
        Message(
            role="user",
            content=(
                "You must call search_convictions to gather evidence "
                "before producing an answer. If the message is a "
                "greeting or unrelated to Decade's convictions, set "
                "out_of_scope=true instead."
            ),
        )
    )


async def _resolve_answer(
    output: AnswerOutput, tool_ctx: ToolContext
) -> tuple[AnswerOutput, StepRecord, OffsetResolution]:
    # Dedupe before resolving so each passage is loaded once even when the
    # model emits one citation per claim.
    output = dedupe_citations(output)
    t0 = perf_counter()
    resolution = await resolve_output(output, ctx=tool_ctx)
    dur = int((perf_counter() - t0) * 1000)
    return output, record_resolver(resolution, duration_ms=dur), resolution


def _assistant_message(response: LLMResponse) -> Message:
    return Message(
        role="assistant",
        content=response.content,
        tool_calls=list(response.tool_calls),
    )


__all__ = ["SYSTEM_PROMPT", "run"]
