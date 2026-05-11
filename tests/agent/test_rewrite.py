"""Tests for the rewrite stage — runs on every turn, doubles as language detector."""

from pathlib import Path

import pytest

from app.agent.rewrite import rewrite_question
from app.agent.schemas import ConversationTurn
from app.providers.base import LLMResponse, TokenUsage
from app.providers.stub import StubLLM, load_stub_responses

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "agent_scenarios"


def _stub_response(rewritten: str, language: str) -> LLMResponse:
    return LLMResponse(
        content=f'{{"rewritten_question":"{rewritten}","detected_language":"{language}"}}',
        tool_calls=[],
        parsed={"rewritten_question": rewritten, "detected_language": language},
        usage=TokenUsage(
            model="stub-llm",
            prompt_tokens=50,
            completion_tokens=12,
            cached_tokens=0,
            reasoning_tokens=0,
        ),
        finish_reason="stop",
    )


@pytest.mark.asyncio
async def test_rewrite_resolves_pt_referent() -> None:
    """A PT history with a PT follow-up rewrites into a self-contained PT question."""
    responses = load_stub_responses(FIXTURES / "rewrite_pt.yaml")
    stub = StubLLM(responses)
    history = [
        ConversationTurn(role="user", content="Como o CDB é tributado?"),
        ConversationTurn(role="assistant", content="O CDB segue a tabela regressiva."),
    ]

    rewritten, language, step = await rewrite_question("E as LCAs?", history, llm=stub)

    assert "LCA" in rewritten
    assert "tribut" in rewritten.lower()
    assert language == "pt"
    assert step.kind == "llm_call"
    assert step.payload["stage"] == "rewrite"
    assert step.payload["history_turns"] == 2
    assert step.payload["detected_language"] == "pt"


@pytest.mark.asyncio
async def test_rewrite_history_block_includes_assistant_text() -> None:
    """The rewrite stage *can* see prior assistant text — that's its job.

    The agent loop never sees it (asserted in test_loop_with_stub.py); this
    test pins down the inverse: rewrite *does* receive it.
    """
    responses = load_stub_responses(FIXTURES / "rewrite_pt.yaml")
    stub = StubLLM(responses)
    history = [
        ConversationTurn(role="user", content="Como o CDB é tributado?"),
        ConversationTurn(role="assistant", content="O CDB segue a tabela regressiva."),
    ]

    await rewrite_question("E as LCAs?", history, llm=stub)

    user_block = stub.calls[0].messages[1].content or ""
    assert "tabela regressiva" in user_block
    assert "Como o CDB é tributado?" in user_block


@pytest.mark.asyncio
async def test_rewrite_passthrough_with_empty_history_still_detects_language() -> None:
    """With no prior turns the rewrite is a passthrough on the question, but
    the model still reports the language — that's why we always call rewrite."""
    stub = StubLLM([_stub_response("como invierto en small caps?", "es")])

    rewritten, language, step = await rewrite_question("como invierto en small caps?", [], llm=stub)

    assert rewritten == "como invierto en small caps?"
    assert language == "es"
    assert step.payload["history_turns"] == 0
    assert step.payload["detected_language"] == "es"
    user_block = stub.calls[0].messages[1].content or ""
    assert "No prior conversation" in user_block


@pytest.mark.asyncio
async def test_rewrite_uses_low_reasoning_effort() -> None:
    """Cost discipline: rewrite is a tiny task. ``low`` is the cheapest
    effort accepted across the whole gpt-5.x family (gpt-5.5+ dropped
    ``minimal``)."""
    responses = load_stub_responses(FIXTURES / "rewrite_pt.yaml")
    stub = StubLLM(responses)
    history = [ConversationTurn(role="user", content="hi")]

    await rewrite_question("ok", history, llm=stub)

    assert stub.calls[0].reasoning_effort == "low"
    assert stub.calls[0].max_output_tokens == 200
    assert stub.calls[0].schema is not None
