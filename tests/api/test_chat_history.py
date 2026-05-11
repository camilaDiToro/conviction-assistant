"""Tests for GET /chat/conversations and /chat/conversations/{id}."""

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
    db_path = tmp_path / "history.sqlite"
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


async def _send_chat(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
    *,
    question: str,
    conversation_id: str | None = None,
) -> dict[str, Any]:
    stub = StubLLM(load_stub_responses(FIXTURES / "basic_search.yaml"))

    async def fake_search(_ctx: ToolContext, **_: Any) -> list[PassageHit]:
        return [_hit()]

    async def fake_read(_ctx: ToolContext, *, passage_ids: list[str]) -> list[Passage]:
        return [_passage() for _ in passage_ids]

    _patch_tools(monkeypatch, {"search_convictions": fake_search, "read_passage": fake_read})
    _patch_passage_repo(monkeypatch)
    app.dependency_overrides[get_llm_provider_dep] = lambda: stub

    body = {"question": question, "history": []}
    if conversation_id:
        body["conversation_id"] = conversation_id
    response = await client.post(
        "/api/chat",
        headers={"X-Chat-Token": "test-chat-token"},
        json=body,
    )
    assert response.status_code == 200, response.text
    return response.json()


# ---- list ----------------------------------------------------------


async def test_list_conversations_empty_returns_empty(client) -> None:
    response = await client.get(
        "/api/chat/conversations",
        headers={"X-Chat-Token": "test-chat-token"},
    )
    assert response.status_code == 200
    assert response.json() == {"conversations": []}


async def test_list_conversations_returns_one_after_chat(
    client, monkeypatch: pytest.MonkeyPatch
) -> None:
    res = await _send_chat(client, monkeypatch, question="What is a CDB?")
    response = await client.get(
        "/api/chat/conversations",
        headers={"X-Chat-Token": "test-chat-token"},
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body["conversations"]) == 1
    item = body["conversations"][0]
    assert item["conversation_id"] == res["conversation_id"]
    assert item["title"] == "What is a CDB?"
    assert item["question_count"] == 1


async def test_list_conversations_orders_by_recency(
    client, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Most recently active conversation should appear first."""
    res_a = await _send_chat(client, monkeypatch, question="Older question")
    res_b = await _send_chat(client, monkeypatch, question="Newer question")
    response = await client.get(
        "/api/chat/conversations",
        headers={"X-Chat-Token": "test-chat-token"},
    )
    body = response.json()
    ids = [c["conversation_id"] for c in body["conversations"]]
    assert ids[0] == res_b["conversation_id"]
    assert ids[1] == res_a["conversation_id"]


async def test_list_conversations_requires_token(client) -> None:
    response = await client.get("/api/chat/conversations")
    assert response.status_code == 401


# ---- load ----------------------------------------------------------


async def test_load_conversation_returns_messages(client, monkeypatch: pytest.MonkeyPatch) -> None:
    sent = await _send_chat(client, monkeypatch, question="What is a CDB?")
    conv_id = sent["conversation_id"]

    response = await client.get(
        f"/api/chat/conversations/{conv_id}",
        headers={"X-Chat-Token": "test-chat-token"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["conversation_id"] == conv_id
    assert len(body["messages"]) == 1
    msg = body["messages"][0]
    assert msg["kind"] == "answer"
    assert msg["user_question"] == "What is a CDB?"
    assert msg["answer"].startswith("CDBs follow")
    cit = msg["citations"][0]
    assert cit["document"] == "cdbs_quick_guide.md"
    assert isinstance(cit["start"], int) and isinstance(cit["end"], int)
    assert cit["passage_text"][cit["start"] : cit["end"]] == "tabela regressiva"
    assert "quote" not in cit
    assert msg["language"] == "en"


async def test_load_conversation_unknown_id_returns_404(client) -> None:
    response = await client.get(
        "/api/chat/conversations/does-not-exist",
        headers={"X-Chat-Token": "test-chat-token"},
    )
    assert response.status_code == 404


async def test_load_conversation_requires_token(client) -> None:
    response = await client.get("/api/chat/conversations/anything")
    assert response.status_code == 401


# ---- per-question steps --------------------------------------------


async def test_question_steps_returns_reconstructed_trace(
    client, monkeypatch: pytest.MonkeyPatch
) -> None:
    sent = await _send_chat(client, monkeypatch, question="What is a CDB?")
    conv_id = sent["conversation_id"]
    qid = sent["question_id"]
    live_steps = sent["debug"]["steps"]

    response = await client.get(
        f"/api/chat/conversations/{conv_id}/questions/{qid}/steps",
        headers={"X-Chat-Token": "test-chat-token"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["conversation_id"] == conv_id
    assert body["question_id"] == qid
    # Reconstruction reproduces every kind from the live trace, in order.
    assert [s["kind"] for s in body["steps"]] == [s["kind"] for s in live_steps]
    assert [s["name"] for s in body["steps"]] == [s["name"] for s in live_steps]
    # step_ids match for the persisted steps; the synthetic trailing
    # ``kind="response"`` step is regenerated server-side per request,
    # so its id doesn't have to match the live one.
    persisted_count = sum(1 for s in live_steps if s["kind"] != "response")
    assert [s["step_id"] for s in body["steps"][:persisted_count]] == [
        s["step_id"] for s in live_steps[:persisted_count]
    ]
    assert body["usage_summary"]["step_count"] == len(live_steps)
    assert "verifier_passed" not in body
    assert body["steps"][-1]["kind"] == "response"
    assert body["steps"][-1]["result"]["output"]["answer"].startswith("CDBs follow")


async def test_question_steps_unknown_question_returns_404(
    client, monkeypatch: pytest.MonkeyPatch
) -> None:
    sent = await _send_chat(client, monkeypatch, question="What is a CDB?")
    conv_id = sent["conversation_id"]
    response = await client.get(
        f"/api/chat/conversations/{conv_id}/questions/does-not-exist/steps",
        headers={"X-Chat-Token": "test-chat-token"},
    )
    assert response.status_code == 404


async def test_question_steps_requires_token(client) -> None:
    response = await client.get(
        "/api/chat/conversations/x/questions/y/steps",
    )
    assert response.status_code == 401


async def test_load_conversation_preserves_order_across_turns(
    client, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Two turns in the same conversation_id round-trip in order."""
    first = await _send_chat(client, monkeypatch, question="Turn one?")
    conv_id = first["conversation_id"]
    await _send_chat(
        client,
        monkeypatch,
        question="Turn two?",
        conversation_id=conv_id,
    )

    response = await client.get(
        f"/api/chat/conversations/{conv_id}",
        headers={"X-Chat-Token": "test-chat-token"},
    )
    body = response.json()
    assert len(body["messages"]) == 2
    assert body["messages"][0]["user_question"] == "Turn one?"
    assert body["messages"][1]["user_question"] == "Turn two?"
