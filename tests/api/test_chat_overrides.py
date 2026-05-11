"""Per-request override tests for POST /chat (B10).

Verifies that ``ChatRequest.overrides`` correctly forwards
``reasoning_effort``/``rewrite_reasoning_effort``/``agent_max_*`` knobs
through the agent loop, and that the model override is gated by
``settings.allowed_models``.

The stub records every ``generate()`` call on ``stub.calls`` (see
``app/providers/stub.py::StubCall``), which is how we assert that the
override actually reached the provider boundary.
"""

from pathlib import Path
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient

from app.agent.tools import ToolContext
from app.config import db, settings
from app.config.db import get_session
from app.main import app
from app.providers.stub import StubLLM, load_stub_responses
from app.retrieval.bm25 import BM25Retriever
from app.schemas import Passage, PassageHit
from tests.api.test_chat import _hit, _override_llm, _passage, _patch_passage_repo, _patch_tools

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "agent_scenarios"


@pytest.fixture
async def client(tmp_path, monkeypatch):
    db_path = tmp_path / "chat.sqlite"
    db.migrate(db_path)
    engine = db.make_engine(f"sqlite+aiosqlite:///{db_path.as_posix()}")
    factory = db.make_session_factory(engine)

    monkeypatch.setattr(settings, "sqlite_path", db_path)
    monkeypatch.setattr(settings, "chat_access_token", "test-chat-token")
    monkeypatch.setattr(settings, "admin_token", "test-admin-token")

    async def _override_session():
        async with factory() as s:
            yield s

    app.dependency_overrides[get_session] = _override_session
    app.state.retriever = BM25Retriever()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
    await engine.dispose()


def _wire_basic_search(monkeypatch: pytest.MonkeyPatch, stub: StubLLM) -> None:
    async def fake_search(_ctx: ToolContext, **_: Any) -> list[PassageHit]:
        return [_hit()]

    async def fake_read(_ctx: ToolContext, *, passage_ids: list[str]) -> list[Passage]:
        return [_passage(pid) for pid in passage_ids]

    _patch_tools(monkeypatch, {"search_convictions": fake_search, "read_passage": fake_read})
    _patch_passage_repo(monkeypatch)
    _override_llm(stub)


async def test_overrides_reasoning_effort_reaches_provider(
    client, monkeypatch: pytest.MonkeyPatch
) -> None:
    stub = StubLLM(load_stub_responses(FIXTURES / "basic_search.yaml"))
    _wire_basic_search(monkeypatch, stub)

    response = await client.post(
        "/api/chat",
        headers={"X-Chat-Token": "test-chat-token"},
        json={
            "question": "What is a CDB?",
            "history": [],
            "overrides": {
                "reasoning_effort": "low",
                "rewrite_reasoning_effort": "minimal",
            },
        },
    )
    assert response.status_code == 200, response.text

    # Rewrite is the first generate() call; agent loop comes after.
    assert stub.calls, "stub never invoked"
    assert stub.calls[0].reasoning_effort == "minimal"
    # Every loop call after the rewrite should run at the override.
    for call in stub.calls[1:]:
        assert call.reasoning_effort == "low"


async def test_overrides_disallowed_model_returns_400(
    client, monkeypatch: pytest.MonkeyPatch
) -> None:
    stub = StubLLM(load_stub_responses(FIXTURES / "basic_search.yaml"))
    _wire_basic_search(monkeypatch, stub)

    response = await client.post(
        "/api/chat",
        headers={"X-Chat-Token": "test-chat-token"},
        json={
            "question": "x",
            "history": [],
            "overrides": {"model": "evil-model-not-in-list"},
        },
    )
    assert response.status_code == 400
    assert "allowed_models" in response.json()["detail"]


async def test_overrides_allowed_model_passes_through(
    client, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An allowed model override should not 400. The stub is still used
    (dependency override stays in place), but the request is accepted."""
    stub = StubLLM(load_stub_responses(FIXTURES / "basic_search.yaml"))
    _wire_basic_search(monkeypatch, stub)

    monkeypatch.setattr(settings, "allowed_models", ["gpt-5", "gpt-5-mini"])

    response = await client.post(
        "/api/chat",
        headers={"X-Chat-Token": "test-chat-token"},
        json={
            "question": "What is a CDB?",
            "history": [],
            "overrides": {"model": "gpt-5"},
        },
    )
    assert response.status_code == 200, response.text


async def test_overrides_bounds_validation(client, monkeypatch: pytest.MonkeyPatch) -> None:
    """``agent_max_tool_calls=99`` is out of bounds (ge=1 le=10) → 422."""
    stub = StubLLM(load_stub_responses(FIXTURES / "basic_search.yaml"))
    _wire_basic_search(monkeypatch, stub)

    response = await client.post(
        "/api/chat",
        headers={"X-Chat-Token": "test-chat-token"},
        json={
            "question": "x",
            "history": [],
            "overrides": {"agent_max_tool_calls": 99},
        },
    )
    assert response.status_code == 422
