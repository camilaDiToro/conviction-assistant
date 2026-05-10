"""Tests for the rewrite stage — the conversation-memory quarantine."""

from pathlib import Path

import pytest

from app.agent.rewrite import rewrite_question
from app.agent.schemas import ConversationTurn
from app.errors import AgentError
from app.providers.stub import StubLLM, load_stub_responses

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "agent_scenarios"


@pytest.mark.asyncio
async def test_rewrite_resolves_pt_referent() -> None:
    """A PT history with a PT follow-up rewrites into a self-contained PT question."""
    responses = load_stub_responses(FIXTURES / "rewrite_pt.yaml")
    stub = StubLLM(responses)
    history = [
        ConversationTurn(role="user", content="Como o CDB é tributado?"),
        ConversationTurn(role="assistant", content="O CDB segue a tabela regressiva."),
    ]

    rewritten, step = await rewrite_question("E as LCAs?", history, llm=stub)

    assert "LCA" in rewritten
    assert "tribut" in rewritten.lower()
    assert step.kind == "llm_call"
    assert step.payload["stage"] == "rewrite"
    assert step.payload["history_turns"] == 2


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
async def test_rewrite_rejects_empty_history() -> None:
    stub = StubLLM([])
    with pytest.raises(AgentError, match="empty history"):
        await rewrite_question("Hi", [], llm=stub)
    assert stub.calls == []  # no LLM call attempted


@pytest.mark.asyncio
async def test_rewrite_uses_minimal_reasoning_effort() -> None:
    """Cost discipline: rewrite is a tiny task, must run with minimal reasoning."""
    responses = load_stub_responses(FIXTURES / "rewrite_pt.yaml")
    stub = StubLLM(responses)
    history = [ConversationTurn(role="user", content="hi")]

    await rewrite_question("ok", history, llm=stub)

    assert stub.calls[0].reasoning_effort == "minimal"
    assert stub.calls[0].max_output_tokens == 200
    assert stub.calls[0].schema is not None
