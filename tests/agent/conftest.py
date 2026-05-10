"""Shared fixtures for agent loop tests.

The offset resolver runs after every ``AnswerOutput``, which means tests
that drive the loop with ``StubLLM`` need a stand-in for
``passages_repo.get`` at the module the loop reaches it from
(``app.agent.audit``). The real one would await on a ``MagicMock``
session and crash. This conftest provides a single autouse fixture that
returns a Passage whose ``text`` is a superset of every verbatim quote
used across the fixture YAMLs in ``tests/fixtures/agent_scenarios/``.

Tests that need a different passage (e.g. ``test_loop_with_resolver.py``
patches its own ``passages_repo.get``) can still override locally —
pytest's monkeypatch resolves last-applied-wins.
"""

from pathlib import Path
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
    )


@pytest.fixture(autouse=True)
def _autopatch_passages_repo(
    request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Patch ``passages_repo.get`` at the audit module the agent loop
    reaches for it. Returns a Passage whose text is a superset of every
    fixture quote. Tests that need a different passage shape can
    re-patch on top.

    Scoped to tests directly under ``tests/agent/`` (the loop tests).
    Subdirectory tests (``tools/``, ``resolver/``) test against real
    passage texts and must not see the patch.
    """
    if Path(request.node.fspath).parent != Path(__file__).parent:
        return

    async def fake_get(_session: Any, passage_id: str) -> Passage:
        return _make_passage(passage_id)

    monkeypatch.setattr("app.agent.audit.passages_repo.get", fake_get)
