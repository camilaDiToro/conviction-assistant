"""End-to-end tests for the agent loop with the offset resolver.

Two scenarios:

1. **Anchored citation.** Verbatim quote → resolver finds the offsets →
   ``AgentResult.resolution`` carries one anchored entry with passage
   provenance and ``(start, end)`` non-null.
2. **Non-anchoring citation.** Paraphrased quote → resolver fails to
   find a substring → entry survives with ``failure_reason='offset_not_found'``
   and ``start/end`` null. The citation is NOT dropped — the popup will
   show the passage without a highlight.
"""

from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from app.agent import run
from app.agent.schemas import AnswerOutput
from app.agent.tools import TOOLS, ToolContext, ToolEntry
from app.providers.stub import StubLLM, load_stub_responses
from app.schemas import Passage, PassageHit

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "agent_scenarios"

# Passage text that the fake passages_repo.get returns. The fixture's
# verbatim quote ("tabela regressiva") is a substring of this text.
PASSAGE_TEXT = "example passage text covering tabela regressiva and position A and position B"


def _stub_ctx() -> ToolContext:
    return ToolContext(session=MagicMock(), retriever=MagicMock())


def _patch_tools(
    monkeypatch: pytest.MonkeyPatch,
    replacements: dict[str, Callable[..., Awaitable[Any]]],
) -> None:
    for name, func in replacements.items():
        original = TOOLS[name]
        monkeypatch.setitem(TOOLS, name, ToolEntry(original.definition, func))


def _passage(passage_id: str = "cdbs_quick_guide#tributacao") -> Passage:
    return Passage(
        id=passage_id,
        document_id=passage_id.split("#")[0],
        document_title="CDBs Quick Guide",
        heading=passage_id.split("#", 1)[-1],
        heading_path=["Tributação"],
        text=PASSAGE_TEXT,
    )


def _hit(passage_id: str = "cdbs_quick_guide#tributacao") -> PassageHit:
    p = _passage(passage_id)
    return PassageHit(
        passage_id=p.id,
        score=1.0,
        document_id=p.document_id,
        document_title=p.document_title,
        heading_path=p.heading_path,
        snippet=p.text[:80],
    )


def _patch_passage_repo(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make ``passages_repo.get_many`` return the fake passage for the
    fixed passage_id used across these tests, omitting unknown ids."""
    fake = _passage()

    async def fake_get_many(_session: Any, ids: Any) -> dict[str, Passage]:
        return {pid: fake for pid in ids if pid == fake.id}

    monkeypatch.setattr("app.agent.audit.passages_repo.get_many", fake_get_many)


def _common_tool_patches(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_search(_ctx: ToolContext, **_: Any) -> list[PassageHit]:
        return [_hit()]

    _patch_tools(monkeypatch, {"search_convictions": fake_search})


# ---- 1. anchored citation ------------------------------------------


@pytest.mark.asyncio
async def test_resolver_anchors_verbatim_quote(monkeypatch: pytest.MonkeyPatch) -> None:
    _common_tool_patches(monkeypatch)
    _patch_passage_repo(monkeypatch)

    stub = StubLLM(load_stub_responses(FIXTURES / "resolver_pass.yaml"))
    result = await run("What is a CDB?", [], tool_ctx=_stub_ctx(), llm=stub)

    assert isinstance(result.output, AnswerOutput)
    # Citation survives intact in the output.
    assert len(result.output.citations) == 1
    assert result.output.citations[0].quote == "tabela regressiva"

    # Exactly one resolver step recorded.
    resolver_steps = [s for s in result.steps if s.kind == "resolver"]
    assert len(resolver_steps) == 1
    payload_entries = resolver_steps[0].payload["entries"]
    assert len(payload_entries) == 1
    assert payload_entries[0]["failure_reason"] is None

    # AgentResult.resolution carries one anchored entry with full provenance.
    assert result.resolution is not None
    assert result.resolution.all_anchored
    assert len(result.resolution.entries) == 1
    e = result.resolution.entries[0]
    assert e.passage_id == "cdbs_quick_guide#tributacao"
    assert e.document_id == "cdbs_quick_guide"
    assert e.document_title == "CDBs Quick Guide"
    assert e.heading_path == ["Tributação"]
    assert e.passage_text == PASSAGE_TEXT
    assert e.start is not None and e.end is not None
    assert PASSAGE_TEXT[e.start : e.end] == "tabela regressiva"


# ---- 2. non-anchoring citation survives ----------------------------


@pytest.mark.asyncio
async def test_resolver_non_anchoring_citation_survives_with_null_offsets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _common_tool_patches(monkeypatch)
    _patch_passage_repo(monkeypatch)

    stub = StubLLM(load_stub_responses(FIXTURES / "resolver_offset_not_found.yaml"))
    result = await run("What is a CDB?", [], tool_ctx=_stub_ctx(), llm=stub)

    assert isinstance(result.output, AnswerOutput)
    # The model's citation survives in the output — the loop does NOT
    # strip non-anchoring citations.
    assert len(result.output.citations) == 1
    assert result.output.citations[0].quote == "regressive IR table"

    # Resolver step recorded the failure.
    resolver_steps = [s for s in result.steps if s.kind == "resolver"]
    assert len(resolver_steps) == 1
    entries = resolver_steps[0].payload["entries"]
    assert entries[0]["failure_reason"] == "offset_not_found"

    # AgentResult.resolution carries one unresolved entry with passage
    # provenance (so the popup can show the passage without a highlight).
    assert result.resolution is not None
    assert not result.resolution.all_anchored
    e = result.resolution.entries[0]
    assert e.failure_reason == "offset_not_found"
    assert e.passage_text == PASSAGE_TEXT
    assert e.start is None and e.end is None
