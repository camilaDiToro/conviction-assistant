"""End-to-end tests for the bounded agent loop, with StubLLM driving.

The loop integrates with real ``TOOLS`` registry entries; tests
monkeypatch each tool's ``func`` to return canned data so we don't need
a real DB session or BM25 index. The stub-LLM drives the *protocol*
side; the patched tools drive the *data* side.
"""

from collections.abc import Awaitable, Callable
from datetime import date
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from app.agent import run
from app.agent.schemas import (
    AnswerOutput,
    ClarifyingQuestionOutput,
    ConversationTurn,
)
from app.agent.tools import TOOLS, ToolContext, ToolEntry
from app.errors import PassageNotFoundError
from app.providers.stub import StubLLM, load_stub_responses
from app.schemas import Passage, PassageHit

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "agent_scenarios"


# ---- helpers --------------------------------------------------------


def _stub_ctx() -> ToolContext:
    """ToolContext with sentinel mocks. Tools are patched per-test, so
    the session and search_index are never actually touched."""
    return ToolContext(session=MagicMock(), retriever=MagicMock())


def _patch_tools(
    monkeypatch: pytest.MonkeyPatch,
    overrides: dict[str, Callable[..., Awaitable[Any]]],
) -> None:
    """Replace `func` on the named TOOLS entries; preserve `definition`."""
    for name, func in overrides.items():
        original = TOOLS[name]
        monkeypatch.setitem(TOOLS, name, ToolEntry(original.definition, func))


def _passage(passage_id: str, *, updated: date | None = date(2026, 4, 1)) -> Passage:
    return Passage(
        id=passage_id,
        document_id=passage_id.split("#")[0],
        document_title=passage_id.split("#")[0].replace("_", " ").title(),
        heading=passage_id.split("#", 1)[-1],
        heading_path=[passage_id.split("#", 1)[-1]],
        text="example passage text covering tabela regressiva and position A and position B",
        document_updated=updated,
    )


def _hit(passage_id: str) -> PassageHit:
    p = _passage(passage_id)
    return PassageHit(
        passage_id=p.id,
        score=1.0,
        document_id=p.document_id,
        document_title=p.document_title,
        heading_path=p.heading_path,
        snippet=p.text[:80],
        document_updated=p.document_updated,
    )


# ---- happy path ----------------------------------------------------


@pytest.mark.asyncio
async def test_basic_search_then_answer(monkeypatch: pytest.MonkeyPatch) -> None:
    """search → read_passage → AnswerOutput. Asserts step ordering, counts,
    and the absence of any prior assistant content in the messages sent."""

    async def fake_search(_ctx: ToolContext, *, query: str, k: int) -> list[PassageHit]:
        assert query == "CDB tributação"
        assert k == 5
        return [_hit("cdbs_quick_guide#tributacao")]

    async def fake_read(_ctx: ToolContext, *, passage_id: str) -> Passage:
        assert passage_id == "cdbs_quick_guide#tributacao"
        return _passage(passage_id)

    _patch_tools(monkeypatch, {"search_convictions": fake_search, "read_passage": fake_read})

    stub = StubLLM(load_stub_responses(FIXTURES / "basic_search.yaml"))
    result = await run("What is a CDB?", [], tool_ctx=_stub_ctx(), llm=stub)

    assert isinstance(result.output, AnswerOutput)
    assert result.output.answer.startswith("CDBs follow")
    assert result.tool_call_count == 2
    assert result.search_count == 1
    assert result.rewritten_question is None  # empty history → no rewrite stage

    kinds = [s.kind for s in result.steps]
    # Step 0 = rewrite stage (always runs, doubles as language detector).
    # B8: a passing verifier step is appended after the final llm_call.
    assert kinds == [
        "llm_call",  # rewrite
        "llm_call",  # agent loop turn 1 (tool decision)
        "tool_call",
        "llm_call",
        "tool_call",
        "llm_call",
        "verifier",
    ]


@pytest.mark.asyncio
async def test_empty_history_runs_passthrough_rewrite(monkeypatch: pytest.MonkeyPatch) -> None:
    """Rewrite stage runs on every turn — on empty history it's a passthrough
    on the question text but still emits ``detected_language`` for the agent
    loop's answer-language directive."""

    async def fake_search(_ctx: ToolContext, **_: Any) -> list[PassageHit]:
        return [_hit("cdbs_quick_guide#tributacao")]

    async def fake_read(_ctx: ToolContext, **_: Any) -> Passage:
        return _passage("cdbs_quick_guide#tributacao")

    _patch_tools(monkeypatch, {"search_convictions": fake_search, "read_passage": fake_read})

    stub = StubLLM(load_stub_responses(FIXTURES / "basic_search.yaml"))
    result = await run("What is a CDB?", [], tool_ctx=_stub_ctx(), llm=stub)

    # Rewrite ran (the fixture's first response is a rewrite stage).
    rewrite_step = result.steps[0]
    assert rewrite_step.kind == "llm_call"
    assert rewrite_step.payload["stage"] == "rewrite"
    assert rewrite_step.payload["history_turns"] == 0
    # `rewritten_question` reported up to the caller stays None on turn 1
    # (the rewrite was a passthrough; nothing to surface).
    assert result.rewritten_question is None


# ---- multi-turn / conversation-memory quarantine ------------------


@pytest.mark.asyncio
async def test_multi_turn_no_assistant_text_in_loop(monkeypatch: pytest.MonkeyPatch) -> None:
    """Critical invariant: prior assistant text MUST NOT appear in the
    messages passed to llm.generate() inside the agent loop."""

    async def fake_search(_ctx: ToolContext, **_: Any) -> list[PassageHit]:
        return [_hit("lca_guide#tributacao")]

    _patch_tools(monkeypatch, {"search_convictions": fake_search})

    stub = StubLLM(load_stub_responses(FIXTURES / "multi_turn_with_rewrite.yaml"))
    history = [
        ConversationTurn(role="user", content="How is CDB taxed?"),
        ConversationTurn(role="assistant", content="CDBs follow the regressive IR table."),
    ]
    result = await run("And what about LCAs?", history, tool_ctx=_stub_ctx(), llm=stub)

    # Call 0 = rewrite stage. Calls 1+ = the agent loop.
    rewrite_call = stub.calls[0]
    loop_calls = stub.calls[1:]

    # The rewrite call SEES the assistant content (that's its job).
    rewrite_user_msg = rewrite_call.messages[1].content or ""
    assert "regressive IR table" in rewrite_user_msg

    # Every agent-loop call has NO assistant content from prior turns.
    for call in loop_calls:
        for msg in call.messages:
            if msg.role == "assistant":
                content = msg.content or ""
                assert "regressive IR table" not in content, (
                    f"prior assistant text leaked into loop call: {content!r}"
                )

    assert result.rewritten_question == "How are LCAs taxed?"
    assert isinstance(result.output, AnswerOutput)


# ---- loop bounds ---------------------------------------------------


@pytest.mark.asyncio
async def test_upper_bound_rejects_sixth_tool_call(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pre-execution batch check: a parallel batch that would push count
    past 5 is rejected entirely; the rejected calls never execute."""
    executed: list[str] = []

    async def fake_search(_ctx: ToolContext, *, query: str, k: int) -> list[PassageHit]:
        executed.append(query)
        return [_hit("cdbs_quick_guide#tributacao")]

    _patch_tools(monkeypatch, {"search_convictions": fake_search})

    stub = StubLLM(load_stub_responses(FIXTURES / "over_budget.yaml"))
    result = await run("X?", [], tool_ctx=_stub_ctx(), llm=stub)

    # First batch (4) executed; second batch (2) rejected; final answer.
    assert executed == ["q1", "q2", "q3", "q4"]
    assert "q5" not in executed
    assert "q6" not in executed
    assert result.tool_call_count == 4  # only executed calls counted
    assert result.search_count == 4

    # 3 LLM calls + 4 tool calls = 7 steps.
    assert sum(1 for s in result.steps if s.kind == "tool_call") == 4
    assert isinstance(result.output, AnswerOutput)
    assert result.output.answer.startswith("Forced final")


@pytest.mark.asyncio
async def test_lower_bound_rejects_pre_search_answer(monkeypatch: pytest.MonkeyPatch) -> None:
    """An AnswerOutput with search_count==0 is rejected; the loop
    appends a system reminder and continues. ClarifyingQuestionOutput
    is exempt — see the next test."""

    async def fake_search(_ctx: ToolContext, **_: Any) -> list[PassageHit]:
        return [_hit("cdbs_quick_guide#tributacao")]

    _patch_tools(monkeypatch, {"search_convictions": fake_search})

    stub = StubLLM(load_stub_responses(FIXTURES / "pre_search_answer.yaml"))
    result = await run("X?", [], tool_ctx=_stub_ctx(), llm=stub)

    assert isinstance(result.output, AnswerOutput)
    assert result.output.answer == "Now grounded."
    assert result.search_count == 1

    # Call 0 = rewrite stage. Calls 1+ = the agent loop. Inside the loop:
    # call 1 was the rejected premature answer; call 2+ retried with the
    # appended reminder. Find any agent-loop call that saw the reminder.
    loop_messages = [m for c in stub.calls[1:] for m in c.messages]
    reminder_msgs = [
        m for m in loop_messages if m.role == "user" and "search_convictions" in (m.content or "")
    ]
    assert len(reminder_msgs) >= 1


@pytest.mark.asyncio
async def test_clarifying_question_exempt_from_lower_bound() -> None:
    """ClarifyingQuestionOutput can be emitted before any search."""
    stub = StubLLM(load_stub_responses(FIXTURES / "clarifying.yaml"))
    result = await run("LCI?", [], tool_ctx=_stub_ctx(), llm=stub)

    assert isinstance(result.output, ClarifyingQuestionOutput)
    assert result.output.question == "Did you mean LCI or LCA?"
    assert result.output.options == ["LCI", "LCA"]
    assert result.search_count == 0
    assert result.tool_call_count == 0


@pytest.mark.asyncio
async def test_out_of_scope_answer_exempt_from_lower_bound() -> None:
    """An AnswerOutput with out_of_scope=true is accepted without a
    prior search — greetings and unrelated topics have nothing to ground."""
    stub = StubLLM(load_stub_responses(FIXTURES / "out_of_scope_no_search.yaml"))
    result = await run("hola", [], tool_ctx=_stub_ctx(), llm=stub)

    assert isinstance(result.output, AnswerOutput)
    assert result.output.out_of_scope is True
    assert result.output.citations == []
    assert result.search_count == 0
    assert result.tool_call_count == 0


# ---- conflict surfacing (Rule B) ----------------------------------


@pytest.mark.asyncio
async def test_dated_conflict_surfaced(monkeypatch: pytest.MonkeyPatch) -> None:
    """Two passages with different dates produce a final answer that
    names both and identifies the newer one."""

    async def fake_search(_ctx: ToolContext, **_: Any) -> list[PassageHit]:
        return [_hit("doc_a#section"), _hit("doc_b#section")]

    async def fake_read(_ctx: ToolContext, *, passage_id: str) -> Passage:
        if passage_id == "doc_a#section":
            return _passage("doc_a#section", updated=date(2026, 4, 1))
        if passage_id == "doc_b#section":
            return _passage("doc_b#section", updated=date(2026, 1, 1))
        raise PassageNotFoundError(passage_id)

    _patch_tools(monkeypatch, {"search_convictions": fake_search, "read_passage": fake_read})

    stub = StubLLM(load_stub_responses(FIXTURES / "dated_conflict.yaml"))
    result = await run("Quem está certo?", [], tool_ctx=_stub_ctx(), llm=stub)

    assert isinstance(result.output, AnswerOutput)
    answer = result.output.answer
    assert "disagree" in answer.lower() or "disagre" in answer.lower()
    assert "Abril 2026" in answer
    assert "Janeiro 2026" in answer


@pytest.mark.asyncio
async def test_undated_conflict_says_undated(monkeypatch: pytest.MonkeyPatch) -> None:
    """Rule B undated clause: when one or both passages are dateless, the
    answer must say so and not silently pick the dated one as 'newer'."""

    async def fake_search(_ctx: ToolContext, **_: Any) -> list[PassageHit]:
        return [_hit("doc_a#section"), _hit("doc_b_undated#section")]

    async def fake_read(_ctx: ToolContext, *, passage_id: str) -> Passage:
        if passage_id == "doc_a#section":
            return _passage("doc_a#section", updated=date(2026, 4, 1))
        if passage_id == "doc_b_undated#section":
            return _passage("doc_b_undated#section", updated=None)
        raise PassageNotFoundError(passage_id)

    _patch_tools(monkeypatch, {"search_convictions": fake_search, "read_passage": fake_read})

    stub = StubLLM(load_stub_responses(FIXTURES / "undated_conflict.yaml"))
    result = await run("Quem está certo?", [], tool_ctx=_stub_ctx(), llm=stub)

    assert isinstance(result.output, AnswerOutput)
    assert "(undated)" in result.output.answer.lower() or "undated" in result.output.answer.lower()


# ---- tool-error feedback ------------------------------------------


@pytest.mark.asyncio
async def test_domain_error_surfaces_to_model(monkeypatch: pytest.MonkeyPatch) -> None:
    """A tool that raises PassageNotFoundError yields an error tool
    message the model can recover from on the next turn."""

    async def fake_read(_ctx: ToolContext, *, passage_id: str) -> Passage:
        if passage_id.startswith("does_not_exist"):
            raise PassageNotFoundError(passage_id)
        return _passage(passage_id)

    async def fake_search(_ctx: ToolContext, **_: Any) -> list[PassageHit]:
        return [_hit("cdbs_quick_guide#tributacao")]

    _patch_tools(monkeypatch, {"read_passage": fake_read, "search_convictions": fake_search})

    stub = StubLLM(load_stub_responses(FIXTURES / "tool_error_feedback.yaml"))
    result = await run("X?", [], tool_ctx=_stub_ctx(), llm=stub)

    assert isinstance(result.output, AnswerOutput)
    assert result.output.answer == "Recovered."

    # Inspect agent-loop messages (calls[0] is the rewrite stage). The tool
    # message for the bad read should contain the error string the model
    # can act on.
    loop_messages = [m for c in stub.calls[1:] for m in c.messages]
    tool_msgs = [m for m in loop_messages if m.role == "tool"]
    assert any("PassageNotFoundError" in (m.content or "") for m in tool_msgs), [
        m.content for m in tool_msgs
    ]
