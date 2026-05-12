"""End-to-end tests for POST /chat.

Uses StubLLM for the agent loop and a real tmp-path SQLite DB for the
audit-log writes. Tools are patched at the registry (same pattern as
``tests/agent/test_loop_with_stub.py``); the resolver's
``passages_repo.get_many`` lookup is patched to return the fixture passage.
"""

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
from app.repositories import audit as audit_repo
from app.retrieval.bm25 import BM25Retriever
from app.schemas import Passage, PassageHit

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "agent_scenarios"


# ---- helpers --------------------------------------------------------


def _passage(passage_id: str = "cdbs_quick_guide#tributacao") -> Passage:
    return Passage(
        id=passage_id,
        document_id=passage_id.split("#")[0],
        document_title="CDBs Quick Guide",
        heading=passage_id.split("#", 1)[-1],
        heading_path=["CDBs Quick Guide", "Tributação"],
        text="example passage text covering tabela regressiva and position A and position B",
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


# ---- fixtures -------------------------------------------------------


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

    # Lifespan doesn't run under ASGITransport — wire up the search
    # index manually.
    app.state.retriever = BM25Retriever()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
    await engine.dispose()


def _override_llm(stub: StubLLM) -> None:
    app.dependency_overrides[get_llm_provider_dep] = lambda: stub


def _wire_basic_search(monkeypatch: pytest.MonkeyPatch, stub: StubLLM) -> None:
    """Patch tools + passage-repo + LLM dep for the basic_search.yaml fixture."""

    async def fake_search(_ctx: ToolContext, **_: Any) -> list[PassageHit]:
        return [_hit()]

    async def fake_read(_ctx: ToolContext, *, passage_ids: list[str]) -> list[Passage]:
        return [_passage(pid) for pid in passage_ids]

    _patch_tools(monkeypatch, {"search_convictions": fake_search, "read_passage": fake_read})
    _patch_passage_repo(monkeypatch)
    _override_llm(stub)


# ---- happy path -----------------------------------------------------


async def test_chat_happy_path(client, monkeypatch: pytest.MonkeyPatch) -> None:
    stub = StubLLM(load_stub_responses(FIXTURES / "basic_search.yaml"))
    _wire_basic_search(monkeypatch, stub)

    response = await client.post(
        "/api/chat",
        headers={"X-Chat-Token": "test-chat-token"},
        json={"question": "What is a CDB?", "history": []},
    )
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["kind"] == "answer"
    assert body["answer"].startswith("CDBs follow")
    assert body["citations"][0]["passage_id"] == "cdbs_quick_guide#tributacao"
    # Filename answer to "which file did this quote come from?"
    assert body["citations"][0]["document"] == "cdbs_quick_guide.md"
    # The quote was anchored to (start, end) of the passage text.
    cit = body["citations"][0]
    assert isinstance(cit["start"], int) and isinstance(cit["end"], int)
    assert cit["passage_text"][cit["start"] : cit["end"]] == "tabela regressiva"
    assert "quote" not in cit
    assert body["disclaimer"].startswith("This response is informational")
    assert "verification_passed" not in body["debug"]
    assert body["usage_summary"]["step_count"] >= 1
    assert body["conversation_id"]
    assert body["question_id"]


# ---- auth -----------------------------------------------------------


async def test_chat_missing_token_returns_401(client) -> None:
    response = await client.post("/api/chat", json={"question": "x", "history": []})
    assert response.status_code == 401
    assert "chat token" in response.json()["detail"]


async def test_chat_wrong_token_returns_401(client) -> None:
    response = await client.post(
        "/api/chat",
        headers={"X-Chat-Token": "wrong"},
        json={"question": "x", "history": []},
    )
    assert response.status_code == 401


async def test_chat_unconfigured_token_returns_503(client, monkeypatch) -> None:
    """Empty token in settings = misconfigured server. Fail closed."""
    monkeypatch.setattr(settings, "chat_access_token", None)
    response = await client.post(
        "/api/chat",
        headers={"X-Chat-Token": "any"},
        json={"question": "x", "history": []},
    )
    assert response.status_code == 503


# ---- language -------------------------------------------------------


async def test_chat_es_question_gets_es_disclaimer(client, monkeypatch: pytest.MonkeyPatch) -> None:
    responses = load_stub_responses(FIXTURES / "basic_search.yaml")
    # The fixture's rewrite stage hardcodes detected_language="en"; flip to
    # "es" so the agent loop & disclaimer mirror the user's question.
    responses[0].parsed["detected_language"] = "es"  # type: ignore[index]
    stub = StubLLM(responses)
    _wire_basic_search(monkeypatch, stub)

    response = await client.post(
        "/api/chat",
        headers={"X-Chat-Token": "test-chat-token"},
        json={"question": "¿Cómo funciona la tributación?", "history": []},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["disclaimer"].startswith("Esta respuesta es informativa")


async def test_chat_pt_question_gets_pt_disclaimer(client, monkeypatch: pytest.MonkeyPatch) -> None:
    responses = load_stub_responses(FIXTURES / "basic_search.yaml")
    responses[0].parsed["detected_language"] = "pt"  # type: ignore[index]
    stub = StubLLM(responses)
    _wire_basic_search(monkeypatch, stub)

    response = await client.post(
        "/api/chat",
        headers={"X-Chat-Token": "test-chat-token"},
        json={"question": "Você sabe o que é um CDB e como é tributado?", "history": []},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["disclaimer"].startswith("Esta resposta é informativa")


# ---- audit log ------------------------------------------------------


async def test_chat_writes_audit_rows(client, monkeypatch: pytest.MonkeyPatch) -> None:
    stub = StubLLM(load_stub_responses(FIXTURES / "basic_search.yaml"))
    _wire_basic_search(monkeypatch, stub)

    response = await client.post(
        "/api/chat",
        headers={"X-Chat-Token": "test-chat-token"},
        json={"question": "What is a CDB?", "history": []},
    )
    assert response.status_code == 200
    conv_id = response.json()["conversation_id"]

    engine = db.make_engine(f"sqlite+aiosqlite:///{settings.sqlite_path.as_posix()}")
    try:
        async with db.make_session_factory(engine)() as s:
            rows = await audit_repo.fetch_by_conversation(s, conv_id)
    finally:
        await engine.dispose()
    assert rows, "expected audit rows for the conversation"
    kinds = [r["kind"] for r in rows]
    assert "response" in kinds
    assert "resolver" in kinds
    assert kinds.count("llm_call") >= 1


# ---- conversation continuation -------------------------------------


async def test_chat_uses_supplied_conversation_id(client, monkeypatch: pytest.MonkeyPatch) -> None:
    """Server honors a client-supplied conversation_id (groups audit rows)."""
    stub = StubLLM(load_stub_responses(FIXTURES / "basic_search.yaml"))
    _wire_basic_search(monkeypatch, stub)

    supplied = "client-supplied-conv-id-1234"
    response = await client.post(
        "/api/chat",
        headers={"X-Chat-Token": "test-chat-token"},
        json={
            "question": "What is a CDB?",
            "history": [],
            "conversation_id": supplied,
        },
    )
    assert response.status_code == 200
    assert response.json()["conversation_id"] == supplied


# ---- clarifying-question branch ------------------------------------


async def test_chat_clarifying_branch(client, monkeypatch: pytest.MonkeyPatch) -> None:
    stub = StubLLM(load_stub_responses(FIXTURES / "clarifying.yaml"))
    _override_llm(stub)
    _patch_passage_repo(monkeypatch)

    response = await client.post(
        "/api/chat",
        headers={"X-Chat-Token": "test-chat-token"},
        json={"question": "LCI?", "history": []},
    )
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["kind"] == "clarifying_question"
    assert body["question"] == "Did you mean LCI or LCA?"
    assert body["options"] == ["LCI", "LCA"]
    # Clarifying responses still get the disclaimer.
    assert body["disclaimer"]
    # No resolver step runs for a clarifying response.
    assert "verification_passed" not in body["debug"]
