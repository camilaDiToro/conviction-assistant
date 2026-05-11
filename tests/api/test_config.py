"""Tests for GET /api/config."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import settings
from app.main import app


@pytest.fixture
async def client(monkeypatch):
    monkeypatch.setattr(settings, "chat_access_token", "test-chat-token")
    monkeypatch.setattr(settings, "admin_token", "test-admin-token")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


async def test_get_config_happy_path(client) -> None:
    response = await client.get(
        "/api/config",
        headers={"X-Chat-Token": "test-chat-token"},
    )
    assert response.status_code == 200, response.text
    body = response.json()

    assert "defaults" in body
    assert "allowed_models" in body
    assert "allowed_reasoning_efforts" in body
    assert "limits" in body

    defaults = body["defaults"]
    assert defaults["model"] == settings.openai_model
    assert defaults["reasoning_effort"] == settings.agent_reasoning_effort
    assert defaults["agent_max_tool_calls"] == settings.agent_max_tool_calls

    assert set(body["allowed_reasoning_efforts"]) == {
        "none",
        "minimal",
        "low",
        "medium",
        "high",
        "xhigh",
    }
    assert settings.openai_model in body["allowed_models"]

    limits = body["limits"]
    assert limits["agent_max_tool_calls"] == {"min": 1, "max": 10}
    assert limits["agent_max_output_tokens"] == {"min": 256, "max": 16384}


async def test_get_config_missing_token_returns_401(client) -> None:
    response = await client.get("/api/config")
    assert response.status_code == 401


async def test_get_config_wrong_token_returns_401(client) -> None:
    response = await client.get(
        "/api/config",
        headers={"X-Chat-Token": "wrong"},
    )
    assert response.status_code == 401
