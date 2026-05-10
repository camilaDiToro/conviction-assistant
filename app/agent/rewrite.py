"""Multi-turn question rewrite — the conversation-memory quarantine.

Architectural commitment (``docs/ARCHITECTURES.md`` § Conversation memory):
prior assistant answers are **never** injected into the agent loop's
tool-call context. The rewrite stage is the only place that *can* see
prior assistant text — and its single output is a self-contained
question. Whatever the assistant said in the past does not flow into
the grounded retrieval path.

This stage runs only when ``history`` is non-empty. The caller
(``app.agent.loop.run``) skips the LLM call and passes the user message
through verbatim on the first turn of a conversation.

The 2026 RAG community consensus on conversational query rewriting:

- Naive blind always-rewriting introduces noise.
- Brute-force full-history hurts via "Lost in the Middle".
- Selective rewriting (only when there is history to resolve against)
  outperforms both.

See ``docs/b7-decisions.md`` for the longer comparison with Claude Code
(which uses compaction, not rewriting — different trust model) and the
OpenAI Agents SDK (full-history sessions — same trust model, also wrong
fit for grounded RAG).
"""

import uuid
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import cast

from app.agent.schemas import (
    REWRITE_OUTPUT_SCHEMA,
    ConversationTurn,
    StepRecord,
)
from app.config import settings
from app.errors import AgentError
from app.providers import LLMProvider, Message

REWRITE_SYSTEM_PROMPT: str = (Path(__file__).parent / "prompts" / "rewrite.md").read_text(
    encoding="utf-8"
)


async def rewrite_question(
    user_message: str,
    history: list[ConversationTurn],
    *,
    llm: LLMProvider,
) -> tuple[str, StepRecord]:
    """Rewrite ``user_message`` into a self-contained question.

    Caller must guarantee ``history`` is non-empty — the orchestrator
    skips this stage when there is nothing to resolve against.
    """
    if not history:
        raise AgentError("rewrite_question called with empty history")

    user_block = _format_history(history) + f"\n\nNew question: {user_message}"
    messages = [
        Message(role="system", content=REWRITE_SYSTEM_PROMPT),
        Message(role="user", content=user_block),
    ]

    t0 = perf_counter()
    response = await llm.generate(
        messages,
        schema=REWRITE_OUTPUT_SCHEMA,
        reasoning_effort=settings.rewrite_reasoning_effort,
        max_output_tokens=settings.rewrite_max_output_tokens,
    )
    rewrite_dur = int((perf_counter() - t0) * 1000)

    if response.parsed is None:
        raise AgentError("rewrite stage: model returned no parsed output")
    rewritten = response.parsed.get("rewritten_question")
    if not isinstance(rewritten, str) or not rewritten.strip():
        raise AgentError("rewrite stage: model returned empty rewritten_question")

    step = StepRecord(
        step_id=str(uuid.uuid4()),
        kind="llm_call",
        timestamp=datetime.now(UTC),
        payload={
            "stage": "rewrite",
            "user_message": user_message,
            "history_turns": len(history),
            "rewritten_question": rewritten,
        },
        usage=response.usage,
        duration_ms=rewrite_dur,
    )
    return cast(str, rewritten), step


def _format_history(history: list[ConversationTurn]) -> str:
    lines = ["Prior conversation:"]
    for turn in history:
        label = "User" if turn.role == "user" else "Assistant"
        lines.append(f"{label}: {turn.content}")
    return "\n".join(lines)
