"""End-to-end tests for the agent loop with the deterministic verifier (B8).

Covers four scenarios:

1. **Pass on first try.** Verbatim quote → no retry, no strip,
   ``AgentResult.verified_citations`` carries full passage provenance.
2. **Retry-then-pass.** Turn 1 paraphrase → verifier fails → loop
   appends per-citation feedback → turn 2 verbatim → pass.
3. **Strip on second failure (partial).** Two citations, one verbatim
   and one paraphrase. After retry the paraphrase still fails → drop
   it, keep the good one.
4. **Strip on second failure (total).** Single paraphrase citation
   that fails twice → strip leaves zero → ``answer`` is replaced
   with a localized safe refusal.
"""

from collections.abc import Awaitable, Callable
from datetime import date
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

# Passage text that the fake passages_repo.get returns. The test
# fixtures' verbatim quotes (e.g. "tabela regressiva", "position A")
# must be substrings of this text.
PASSAGE_TEXT = "example passage text covering tabela regressiva and position A and position B"


# ---- helpers --------------------------------------------------------


def _stub_ctx() -> ToolContext:
    return ToolContext(session=MagicMock(), retriever=MagicMock())


def _patch_tools(
    monkeypatch: pytest.MonkeyPatch,
    overrides: dict[str, Callable[..., Awaitable[Any]]],
) -> None:
    for name, func in overrides.items():
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
        document_updated=date(2026, 4, 1),
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
        document_updated=p.document_updated,
    )


def _patch_passage_repo(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make ``passages_repo.get`` return the fake passage for the fixed
    passage_id used across these tests, ``None`` otherwise. Patched at
    both modules where the agent loop reaches the repo.
    """
    fake = _passage()

    async def fake_get(_session: Any, passage_id: str) -> Passage | None:
        return fake if passage_id == fake.id else None

    monkeypatch.setattr("app.agent.audit.passages_repo.get", fake_get)
    monkeypatch.setattr("app.agent.retry_policy.passages_repo.get", fake_get)


def _common_tool_patches(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_search(_ctx: ToolContext, **_: Any) -> list[PassageHit]:
        return [_hit()]

    _patch_tools(monkeypatch, {"search_convictions": fake_search})


# ---- 1. pass on first try ------------------------------------------


@pytest.mark.asyncio
async def test_verifier_pass_on_first_try(monkeypatch: pytest.MonkeyPatch) -> None:
    _common_tool_patches(monkeypatch)
    _patch_passage_repo(monkeypatch)

    stub = StubLLM(load_stub_responses(FIXTURES / "verifier_pass.yaml"))
    result = await run("What is a CDB?", [], tool_ctx=_stub_ctx(), llm=stub)

    assert isinstance(result.output, AnswerOutput)
    # Citation survived intact.
    assert len(result.output.citations) == 1
    assert result.output.citations[0].quote == "tabela regressiva"

    # Exactly one verifier step recorded, with attempt=0 and all_passed.
    verifier_steps = [s for s in result.steps if s.kind == "verifier"]
    assert len(verifier_steps) == 1
    assert verifier_steps[0].payload["attempt"] == 0
    assert verifier_steps[0].payload["all_passed"] is True

    # verified_citations carries full provenance for the survived citation.
    assert result.verified_citations is not None
    assert len(result.verified_citations) == 1
    vc = result.verified_citations[0]
    assert vc.passage_id == "cdbs_quick_guide#tributacao"
    assert vc.document_id == "cdbs_quick_guide"
    assert vc.document_title == "CDBs Quick Guide"
    assert vc.heading_path == ["Tributação"]
    assert vc.document_updated == date(2026, 4, 1)
    assert vc.quote == "tabela regressiva"


# ---- 2. retry-then-pass --------------------------------------------


@pytest.mark.asyncio
async def test_verifier_retry_then_pass(monkeypatch: pytest.MonkeyPatch) -> None:
    _common_tool_patches(monkeypatch)
    _patch_passage_repo(monkeypatch)

    stub = StubLLM(load_stub_responses(FIXTURES / "verifier_retry_then_pass.yaml"))
    result = await run("What is a CDB?", [], tool_ctx=_stub_ctx(), llm=stub)

    assert isinstance(result.output, AnswerOutput)
    # Final citation is the verbatim retry.
    assert result.output.citations[0].quote == "tabela regressiva"

    # Two verifier steps: attempt=0 (fail) and attempt=1 (pass).
    verifier_steps = [s for s in result.steps if s.kind == "verifier"]
    assert len(verifier_steps) == 2
    assert verifier_steps[0].payload["attempt"] == 0
    assert verifier_steps[0].payload["all_passed"] is False
    assert verifier_steps[1].payload["attempt"] == 1
    assert verifier_steps[1].payload["all_passed"] is True

    # The retry feedback message must have included passage_id and the
    # original (paraphrased) quote so the model knew what to fix.
    # That's the second-to-last user message before the second LLM call.
    second_call = stub.calls[2]  # call 0 = search; call 1 = answer (paraphrase); call 2 = retry
    last_user = next(m for m in reversed(second_call.messages) if m.role == "user")
    assert last_user.content is not None
    assert "regressive IR table" in last_user.content
    assert "cdbs_quick_guide#tributacao" in last_user.content

    # verified_citations aligns with the surviving (retried) citation.
    assert result.verified_citations is not None
    assert len(result.verified_citations) == 1
    assert result.verified_citations[0].quote == "tabela regressiva"


# ---- 3. strip on second failure (partial) ---------------------------


@pytest.mark.asyncio
async def test_verifier_double_fail_strips_failed_citation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _common_tool_patches(monkeypatch)
    _patch_passage_repo(monkeypatch)

    stub = StubLLM(load_stub_responses(FIXTURES / "verifier_double_fail_strip.yaml"))
    result = await run("What is a CDB?", [], tool_ctx=_stub_ctx(), llm=stub)

    assert isinstance(result.output, AnswerOutput)
    # Original answer was 2 citations; 1 was paraphrase → stripped.
    assert len(result.output.citations) == 1
    assert result.output.citations[0].quote == "position A"
    # Answer text is unchanged from the model's last attempt.
    assert result.output.answer == "Two-claim answer."

    # Two verifier steps; both failed (the loop did NOT escape via pass).
    verifier_steps = [s for s in result.steps if s.kind == "verifier"]
    assert len(verifier_steps) == 2
    assert all(s.payload["all_passed"] is False for s in verifier_steps)

    # verified_citations carries the survivor only.
    assert result.verified_citations is not None
    assert len(result.verified_citations) == 1
    assert result.verified_citations[0].quote == "position A"


# ---- 4. strip on second failure (total) ----------------------------


@pytest.mark.asyncio
async def test_verifier_double_fail_zero_grounded_localized_refusal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _common_tool_patches(monkeypatch)
    _patch_passage_repo(monkeypatch)

    stub = StubLLM(load_stub_responses(FIXTURES / "verifier_double_fail_zero_grounded.yaml"))
    result = await run("What is a CDB?", [], tool_ctx=_stub_ctx(), llm=stub)

    assert isinstance(result.output, AnswerOutput)
    # Single paraphrase citation stripped → zero remain → refusal.
    assert result.output.citations == []
    assert result.output.out_of_scope is False
    assert result.output.general_knowledge_used is False

    # English question → English refusal text.
    assert "verbatim quote" in result.output.answer.lower()
    assert "decade" in result.output.answer.lower()

    # verified_citations is empty (refusal carries zero verified rows).
    assert result.verified_citations == []


# ---- language detection: PT refusal -------------------------------


@pytest.mark.asyncio
async def test_verifier_double_fail_pt_question_yields_pt_refusal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Same fixture as zero-grounded, but the user question is in PT —
    the inline language detector should pick PT for the refusal text.
    """
    _common_tool_patches(monkeypatch)
    _patch_passage_repo(monkeypatch)

    stub = StubLLM(load_stub_responses(FIXTURES / "verifier_double_fail_zero_grounded.yaml"))
    result = await run(
        "Como funciona a tributação do CDB? Você é capaz de responder?",
        [],
        tool_ctx=_stub_ctx(),
        llm=stub,
    )

    assert isinstance(result.output, AnswerOutput)
    assert result.output.citations == []
    # PT refusal contains the marker word "convicções".
    assert "convicções" in result.output.answer.lower()


# ---- verifier-disabled escape hatch -------------------------------


@pytest.mark.asyncio
async def test_verifier_disabled_skips_verification(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When ``settings.verifier_enabled=False``, the loop returns the
    raw AnswerOutput without running the verifier. ``verified_citations``
    is None to signal the verifier did not run."""
    _common_tool_patches(monkeypatch)
    # No need to patch passages_repo — the verifier should never be called.
    monkeypatch.setattr("app.agent.loop.settings.verifier_enabled", False)

    # Reuse the retry-then-pass fixture but only the first AnswerOutput
    # is consumed because verification is skipped — drop the second.
    stub = StubLLM(
        load_stub_responses(FIXTURES / "verifier_retry_then_pass.yaml")[:2]  # search + first answer
    )
    result = await run("What is a CDB?", [], tool_ctx=_stub_ctx(), llm=stub)

    assert isinstance(result.output, AnswerOutput)
    # No verifier steps recorded.
    assert all(s.kind != "verifier" for s in result.steps)
    # Paraphrase citation survives because no check ran.
    assert result.output.citations[0].quote == "regressive IR table"
    # verified_citations is None because verifier did not run.
    assert result.verified_citations is None
