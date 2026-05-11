"""Question rewrite + language detection — runs on every turn.

Architectural commitment (``docs/ARCHITECTURES.md`` § Conversation memory):
prior assistant answers are **never** injected into the agent loop's
tool-call context. The rewrite stage is the only place that *can* see
prior assistant text — and its single output is a self-contained
question. Whatever the assistant said in the past does not flow into
the grounded retrieval path.

This stage runs on **every turn** (turn 1 included) for one extra
reason: it doubles as the language detector. The model's classification
of the user's language drives the answer-language directive in the
agent loop. On turn 1 with no history the rewrite is a passthrough; the
language signal is the load-bearing output.

The 2026 RAG community consensus on conversational query rewriting:

- Naive blind always-rewriting introduces noise.
- Brute-force full-history hurts via "Lost in the Middle".
- Selective rewriting (only when there is history to resolve against)
  outperforms both — the prompt enforces the "echo unchanged" rule
  whenever the new question is already self-contained.

Claude Code uses compaction, not rewriting (different trust model); the
OpenAI Agents SDK uses full-history sessions (same trust model, also
wrong fit for grounded RAG).
"""

import uuid
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import Literal, cast

from app.agent.overrides import AgentOverrides
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

_VALID_LANGUAGES: frozenset[str] = frozenset({"pt", "es", "en"})


async def rewrite_question(
    user_message: str,
    history: list[ConversationTurn],
    *,
    llm: LLMProvider,
    overrides: AgentOverrides | None = None,
) -> tuple[str, Literal["pt", "es", "en"], StepRecord]:
    """Rewrite ``user_message`` into a self-contained question and detect its language.

    Runs on every turn. With empty ``history`` the model returns the
    question unchanged but still classifies the language.
    """
    overrides = overrides or AgentOverrides()
    rewrite_effort = overrides.rewrite_reasoning_effort or settings.rewrite_reasoning_effort

    if history:
        user_block = _format_history(history) + f"\n\nNew question: {user_message}"
    else:
        user_block = f"No prior conversation.\n\nNew question: {user_message}"

    messages = [
        Message(role="system", content=REWRITE_SYSTEM_PROMPT),
        Message(role="user", content=user_block),
    ]

    t0 = perf_counter()
    response = await llm.generate(
        messages,
        schema=REWRITE_OUTPUT_SCHEMA,
        reasoning_effort=rewrite_effort,
        max_output_tokens=settings.rewrite_max_output_tokens,
    )
    rewrite_dur = int((perf_counter() - t0) * 1000)

    if response.parsed is None:
        raise AgentError("rewrite stage: model returned no parsed output")
    rewritten = response.parsed.get("rewritten_question")
    if not isinstance(rewritten, str) or not rewritten.strip():
        raise AgentError("rewrite stage: model returned empty rewritten_question")
    language_raw = response.parsed.get("detected_language")
    if language_raw not in _VALID_LANGUAGES:
        raise AgentError(
            f"rewrite stage: model returned invalid detected_language={language_raw!r}"
        )
    language = cast(Literal["pt", "es", "en"], language_raw)

    step = StepRecord(
        step_id=str(uuid.uuid4()),
        kind="llm_call",
        timestamp=datetime.now(UTC),
        payload={
            "stage": "rewrite",
            "user_message": user_message,
            "history_turns": len(history),
            "rewritten_question": rewritten,
            "detected_language": language,
        },
        usage=response.usage,
        duration_ms=rewrite_dur,
    )
    return cast(str, rewritten), language, step


def _format_history(history: list[ConversationTurn]) -> str:
    lines = ["Prior conversation:"]
    for turn in history:
        label = "User" if turn.role == "user" else "Assistant"
        lines.append(f"{label}: {turn.content}")
    return "\n".join(lines)
