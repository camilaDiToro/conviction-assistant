"""Tests for POST /admin/ingest — exercises router → service → repository."""

from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import db, settings
from app.config.db import get_session
from app.main import app
from app.services.search import BM25Index

CONVICTIONS = Path(__file__).resolve().parents[2] / "convictions"


@pytest.fixture
async def client(tmp_path, monkeypatch):
    db_path = tmp_path / "test.sqlite"
    db.migrate(db_path)
    engine = db.make_engine(f"sqlite+aiosqlite:///{db_path.as_posix()}")
    factory = db.make_session_factory(engine)

    monkeypatch.setattr(settings, "sqlite_path", db_path)
    monkeypatch.setattr(settings, "convictions_dir", CONVICTIONS)

    async def _override():
        async with factory() as s:
            yield s

    app.dependency_overrides[get_session] = _override
    # Lifespan doesn't run under ASGITransport; attach the search index manually
    # so the admin ingest handler's rebuild() call has somewhere to land.
    app.state.search_index = BM25Index()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.mark.skipif(not CONVICTIONS.is_dir(), reason="corpus not found")
async def test_admin_ingest_returns_summary(client):
    response = await client.post("/admin/ingest")
    assert response.status_code == 200
    payload = response.json()
    assert payload["documents"] == 30
    assert payload["passages"] == 423
    assert payload["orphans_deleted"] == 0
    assert payload["db_path"].endswith(".sqlite")


async def test_admin_ingest_returns_400_for_missing_directory(client, monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "convictions_dir", tmp_path / "does-not-exist")
    response = await client.post("/admin/ingest")
    assert response.status_code == 400
    assert "not a directory" in response.json()["detail"]
