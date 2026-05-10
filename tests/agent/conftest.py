"""Shared fixtures for agent loop tests.

The B8 verifier runs by default after every ``AnswerOutput``, which
means tests that drive the loop with ``StubLLM`` need a stand-in for
``app.agent.loop.passages_repo.get`` (the real one would await on a
``MagicMock`` session and crash). This conftest provides a single
autouse fixture that returns a Passage whose ``text`` is a superset
of every verbatim quote used across the fixture YAMLs in
``tests/fixtures/agent_scenarios/``.

Tests that need a different passage (e.g. ``test_loop_with_verifier.py``
patches its own ``passages_repo.get`` for the partial-strip scenario)
can still override locally — pytest's monkeypatch resolves last-applied-wins.
"""

from datetime import date
from typing import Any

import pytest

from app.schemas.passage import Passage

_DEFAULT_TEXT = (
    "example passage text covering tabela regressiva and position A and "
    "position B and isento de imposto de renda"
)


def _make_passage(passage_id: str) -> Passage:
    doc_id = passage_id.split("#")[0]
    return Passage(
        id=passage_id,
        document_id=doc_id,
        document_title=doc_id.replace("_", " ").title(),
        heading=passage_id.split("#", 1)[-1] if "#" in passage_id else "sec",
        heading_path=[passage_id.split("#", 1)[-1] if "#" in passage_id else "sec"],
        text=_DEFAULT_TEXT,
        document_updated=date(2026, 4, 1),
    )


@pytest.fixture(autouse=True)
def _autopatch_passages_repo(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make ``app.agent.loop.passages_repo.get`` return a Passage whose
    text is a superset of every fixture quote. Tests that need a
    different passage shape can re-patch on top of this one.
    """

    async def fake_get(_session: Any, passage_id: str) -> Passage:
        return _make_passage(passage_id)

    monkeypatch.setattr("app.agent.loop.passages_repo.get", fake_get)
