"""Rewrite the user message into a self-contained question and detect its language.

Takes the new message plus prior turns and produces one question with
all the context inlined — so the agent loop can search without seeing
any prior assistant text (grounding stays anchored to the corpus, not
to past answers). Runs on every turn because the same call also
classifies the user's language, which drives the answer-language
directive downstream.
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
from app.i18n import SUPPORTED_LANGUAGES, Language
from app.providers import LLMProvider, Message

REWRITE_SYSTEM_PROMPT: str = (Path(__file__).parent / "prompts" / "rewrite.md").read_text(
    encoding="utf-8"
)


async def rewrite_question(
    user_message: str,
    history: list[ConversationTurn],
    *,
    llm: LLMProvider,
) -> tuple[str, Language, StepRecord]:
    """Rewrite ``user_message`` into a self-contained question and detect its language.

    Runs on every turn. With empty ``history`` the model returns the
    question unchanged but still classifies the language.
    """
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
        reasoning_effort=settings.rewrite_reasoning_effort,
        max_output_tokens=settings.rewrite_max_output_tokens,
    )
    rewrite_dur = int((perf_counter() - t0) * 1000)

    if response.parsed is None:
        raise AgentError("rewrite stage: model returned no parsed output")
    rewritten = response.parsed.get("rewritten_question")
    if not isinstance(rewritten, str) or not rewritten.strip():
        raise AgentError("rewrite stage: model returned empty rewritten_question")
    language_raw = response.parsed.get("detected_language")
    if language_raw not in SUPPORTED_LANGUAGES:
        raise AgentError(
            f"rewrite stage: model returned invalid detected_language={language_raw!r}"
        )
    language = cast(Language, language_raw)

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
    return rewritten, language, step


def _format_history(history: list[ConversationTurn]) -> str:
    lines = ["Prior conversation:"]
    for turn in history:
        label = "User" if turn.role == "user" else "Assistant"
        lines.append(f"{label}: {turn.content}")
    return "\n".join(lines)
