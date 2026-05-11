"""Tests for GET /admin/conversations/{id}."""

from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient

from app.agent.tools import TOOLS, ToolContext, ToolEntry
from app.api.deps import get_llm_provider_dep
from app.config import db, settings
from app.config.db import get_session
from app.main import app
from app.providers.stub import StubLLM, load_stub_responses
from app.retrieval.bm25 import BM25Retriever
from app.schemas import Passage, PassageHit

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "agent_scenarios"


def _passage() -> Passage:
    return Passage(
        id="cdbs_quick_guide#tributacao",
        document_id="cdbs_quick_guide",
        document_title="CDBs Quick Guide",
        heading="tributacao",
        heading_path=["CDBs Quick Guide", "Tributação"],
        text="example passage text covering tabela regressiva and position A and position B",
    )


def _hit() -> PassageHit:
    p = _passage()
    return PassageHit(
        passage_id=p.id,
        score=1.0,
        document_id=p.document_id,
        document_title=p.document_title,
        heading_path=p.heading_path,
        snippet=p.text[:80],
    )


def _patch_tools(
    monkeypatch: pytest.MonkeyPatch,
    replacements: dict[str, Callable[..., Awaitable[Any]]],
) -> None:
    for name, func in replacements.items():
        original = TOOLS[name]
        monkeypatch.setitem(TOOLS, name, ToolEntry(original.definition, func))


def _patch_passage_repo(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _passage()

    async def fake_get_many(_session: Any, ids: Any) -> dict[str, Passage]:
        return {pid: fake for pid in ids if pid == fake.id}

    monkeypatch.setattr("app.agent.audit.passages_repo.get_many", fake_get_many)


@pytest.fixture
async def client(tmp_path, monkeypatch):
    db_path = tmp_path / "convs.sqlite"
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


async def _seed_one_chat(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> str:
    stub = StubLLM(load_stub_responses(FIXTURES / "basic_search.yaml"))

    async def fake_search(_ctx: ToolContext, **_: Any) -> list[PassageHit]:
        return [_hit()]

    async def fake_read(_ctx: ToolContext, *, passage_ids: list[str]) -> list[Passage]:
        return [_passage() for _ in passage_ids]

    _patch_tools(monkeypatch, {"search_convictions": fake_search, "read_passage": fake_read})
    _patch_passage_repo(monkeypatch)
    app.dependency_overrides[get_llm_provider_dep] = lambda: stub

    response = await client.post(
        "/api/chat",
        headers={"X-Chat-Token": "test-chat-token"},
        json={"question": "What is a CDB?", "history": []},
    )
    assert response.status_code == 200, response.text
    return response.json()["conversation_id"]


# ---- trace endpoint --------------------------------------------------


async def test_get_conversation_trace_returns_summary(
    client, monkeypatch: pytest.MonkeyPatch
) -> None:
    conv_id = await _seed_one_chat(client, monkeypatch)
    response = await client.get(
        f"/api/admin/conversations/{conv_id}",
        headers={"X-Admin-Token": "test-admin-token"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["conversation_id"] == conv_id
    assert len(body["questions"]) == 1
    q = body["questions"][0]
    assert q["retriever"] == "bm25"
    assert q["answer_or_question"]["kind"] == "answer"
    assert q["step_kinds"]


async def test_get_conversation_trace_unknown_id_returns_404(client) -> None:
    response = await client.get(
        "/api/admin/conversations/does-not-exist",
        headers={"X-Admin-Token": "test-admin-token"},
    )
    assert response.status_code == 404


async def test_get_conversation_trace_requires_admin_token(client) -> None:
    response = await client.get("/api/admin/conversations/anything")
    assert response.status_code == 401


async def test_get_conversation_trace_wrong_token_returns_401(client) -> None:
    response = await client.get(
        "/api/admin/conversations/anything",
        headers={"X-Admin-Token": "wrong"},
    )
    assert response.status_code == 401
