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
- **Deterministic citation verifier (B8).** Every ``AnswerOutput`` is
  substring-verified. First failure → retry with feedback. Second
  failure → strip failed citations; if zero grounded citations remain,
  fall through to a localized safe refusal.

Helpers live in sibling modules: tool dispatch in :mod:`app.agent.tool_dispatch`,
step recorders + verify adapter in :mod:`app.agent.audit`, retry policy
in :mod:`app.agent.retry_policy`, language detection in :mod:`app.agent.language`.
"""

import asyncio
import json
from pathlib import Path

from pydantic import TypeAdapter, ValidationError

from app.agent import retry_policy
from app.agent.audit import (
    record_llm_call,
    record_tool_call,
    record_verifier,
    verify_output,
)
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
from app.agent.verifier import VerificationResult
from app.config import settings
from app.errors import AgentError
from app.providers import LLMProvider, LLMResponse, Message
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
    the agent loop sees ``user_message`` verbatim. On turn 2+ the rewrite
    stage produces a self-contained question.
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

    output, loop_steps, tool_count, search_count, verify_result = await _agent_loop(
        loop_input, tool_ctx=tool_ctx, llm=llm
    )
    steps.extend(loop_steps)

    verified_citations = (
        list(verify_result.verified)
        if isinstance(output, AnswerOutput) and verify_result is not None
        else None
    )

    return AgentResult(
        output=output,
        rewritten_question=rewritten_question,
        steps=steps,
        tool_call_count=tool_count,
        search_count=search_count,
        verified_citations=verified_citations,
    )


async def _agent_loop(
    question: str,
    *,
    tool_ctx: ToolContext,
    llm: LLMProvider,
) -> tuple[AgentOutput, list[StepRecord], int, int, VerificationResult | None]:
    # Loop bounds are read from settings at call time so .env overrides
    # take effect without restart; see app/config/settings.py.
    max_tool_calls = settings.agent_max_tool_calls
    max_iterations = settings.agent_max_iterations
    verifier_enabled = settings.verifier_enabled
    verifier_retry_budget = settings.verifier_retry_budget

    messages: list[Message] = [
        Message(role="system", content=SYSTEM_PROMPT),
        Message(role="user", content=question),
    ]
    tool_definitions = [entry.definition for entry in TOOLS.values()]
    steps: list[StepRecord] = []
    tool_call_count = 0  # invariant: equals the number of *executed* tool calls
    search_count = 0
    verify_attempts = 0  # number of failed verify cycles already consumed
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
        steps.append(record_llm_call(response, stage="agent_loop"))

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
            results = await asyncio.gather(
                *[execute_tool(tc, tool_ctx) for tc in response.tool_calls]
            )
            for tc, result_text in zip(response.tool_calls, results, strict=True):
                messages.append(Message(role="tool", tool_call_id=tc.id, content=result_text))
                steps.append(record_tool_call(tc, result_text))

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
            # prior search. ClarifyingQuestionOutput is always allowed.
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

            # ---- Verifier hook (B8) ---------------------------------
            # Skipped for ClarifyingQuestionOutput (no citations) and
            # when the operator disables it via settings.
            if isinstance(output, AnswerOutput) and verifier_enabled:
                verify = await verify_output(output, ctx=tool_ctx)
                steps.append(record_verifier(verify, attempt=verify_attempts))

                if not verify.all_passed:
                    if verify_attempts < verifier_retry_budget:
                        verify_attempts += 1
                        content = response.content or json.dumps(response.parsed)
                        messages.append(Message(role="assistant", content=content))
                        messages.append(
                            Message(
                                role="user",
                                content=await retry_policy.compose_feedback(verify, ctx=tool_ctx),
                            )
                        )
                        continue
                    # Second failure → strip failed citations. If none
                    # survive, fall through to a localized safe refusal.
                    output = retry_policy.strip_failed_citations(output, verify)
                    if not output.citations:
                        output = retry_policy.localized_refusal(question)
                        verify = VerificationResult(verified=[], failures=[])

                return output, steps, tool_call_count, search_count, verify

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
