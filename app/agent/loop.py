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
- **Deterministic offset resolver.** Every ``AnswerOutput`` runs through
  the resolver: each citation's verbatim quote is turned into a
  ``(start, end)`` region of the cited passage, and the literal quote
  is dropped before the response is built. Non-anchoring citations
  survive with offsets ``None`` — the popup shows the passage with no
  highlight.

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
    """Run one full agent turn.

    The rewrite stage runs on **every** turn — it doubles as the language
    classifier whose output drives the answer-language directive. With
    empty history the rewrite is a passthrough on the question text but
    still emits ``detected_language``.

    Runtime tuning comes from server settings. The public ``/chat``
    contract intentionally has no request-level knobs; one deployed
    server exposes one configured agent behavior.
    """
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
    # Loop bounds read from settings. There are no request-level tuning knobs.
    max_tool_calls = settings.agent_max_tool_calls
    max_iterations = settings.agent_max_iterations
    reasoning_effort = settings.agent_reasoning_effort
    max_output_tokens = settings.agent_max_output_tokens

    # Deterministic language directive — the system prompt's language
    # mirroring rule is sometimes ignored by the model when the cited
    # passages are in a different language than the user's question
    # (observed: ES question, PT corpus, PT answer). Pinning the answer
    # language here removes that drift.
    lang_name = _LANGUAGE_NAME[language]
    language_directive = (
        f"ANSWER LANGUAGE: {lang_name} ({language}). "
        f"You MUST write the `answer` field and any clarifying `question` "
        f"in {lang_name}, regardless of the language of the cited passages. "
        f"Citation `quote` fields stay in their source language."
    )
    messages: list[Message] = [
        Message(role="system", content=SYSTEM_PROMPT),
        Message(role="system", content=language_directive),
        Message(role="user", content=question),
    ]
    tool_definitions = [entry.definition for entry in TOOLS.values()]
    steps: list[StepRecord] = []
    tool_call_count = 0  # invariant: equals the number of *executed* tool calls
    search_count = 0
    budget_exhausted = False

    for _ in range(max_iterations):
        force_final = budget_exhausted or tool_call_count >= max_tool_calls

        t0 = perf_counter()
        response = await llm.generate(
            messages,
            tools=None if force_final else tool_definitions,
            schema=AGENT_OUTPUT_SCHEMA,
            reasoning_effort=reasoning_effort,
            max_output_tokens=max_output_tokens,
        )
        llm_dur = int((perf_counter() - t0) * 1000)
        steps.append(record_llm_call(response, stage="agent_loop", duration_ms=llm_dur))

        # ---- Branch 1: model wants to call tools -----------------
        if response.tool_calls and not force_final:
            # Strict cap — never execute a call past the budget. If the
            # response would push us over, refuse all tool calls in this
            # batch and force a final answer next iteration.
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

            async def _timed_exec(tc):  # type: ignore[no-untyped-def]
                ts = perf_counter()
                text = await execute_tool(tc, tool_ctx)
                return text, int((perf_counter() - ts) * 1000)

            timed_results = await asyncio.gather(*[_timed_exec(tc) for tc in response.tool_calls])
            for tc, (result_text, tc_dur) in zip(response.tool_calls, timed_results, strict=True):
                messages.append(Message(role="tool", tool_call_id=tc.id, content=result_text))
                steps.append(record_tool_call(tc, result_text, duration_ms=tc_dur))

            tool_call_count += len(response.tool_calls)
            search_count += sum(1 for tc in response.tool_calls if tc.name == "search_convictions")
            continue

        # ---- Branch 2: model produced structured output -----------
        if response.parsed is not None:
            try:
                output = _AGENT_OUTPUT_ADAPTER.validate_python(response.parsed)
            except ValidationError as exc:
                raise AgentError(f"model output failed schema validation: {exc}") from exc

            # Lower-bound enforcement — only in-scope grounded answers
            # require a prior search. ClarifyingQuestionOutput is always
            # allowed. Out-of-scope replies (greetings, unrelated topics)
            # also bypass the rule: there is nothing to search for.
            if isinstance(output, AnswerOutput) and search_count == 0 and not output.out_of_scope:
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
                continue

            # ---- Resolver hook ---------------------------------------
            # Collapse duplicate citations first (the model often emits
            # one per claim) so the resolver only loads each passage
            # once. ClarifyingQuestionOutput has no citations to resolve.
            if isinstance(output, AnswerOutput):
                output = dedupe_citations(output)
                tv = perf_counter()
                resolution = await resolve_output(output, ctx=tool_ctx)
                v_dur = int((perf_counter() - tv) * 1000)
                steps.append(record_resolver(resolution, duration_ms=v_dur))
                return output, steps, tool_call_count, search_count, resolution

            return output, steps, tool_call_count, search_count, None

        # Defensive — schema attached but neither tool_calls nor parsed.
        # Strict mode should make this unreachable.
        raise AgentError("model returned neither tool_calls nor parsed output")

    raise AgentError(f"agent loop exceeded {max_iterations} iterations")


def _assistant_message(response: LLMResponse) -> Message:
    return Message(
        role="assistant",
        content=response.content,
        tool_calls=list(response.tool_calls),
    )


__all__ = ["SYSTEM_PROMPT", "run"]
