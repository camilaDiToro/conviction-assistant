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

    assert body == {"model": settings.openai_model}


async def test_get_config_missing_token_returns_401(client) -> None:
    response = await client.get("/api/config")
    assert response.status_code == 401


async def test_get_config_wrong_token_returns_401(client) -> None:
    response = await client.get(
        "/api/config",
        headers={"X-Chat-Token": "wrong"},
    )
    assert response.status_code == 401
