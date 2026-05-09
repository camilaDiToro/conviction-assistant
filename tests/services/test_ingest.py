"""Tests for app/services/ingest.py — pure service-layer behavior over a fresh DB."""

from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import db
from app.errors import IngestError
from app.repositories import passages as passages_repo
from app.services.ingest import ingest_corpus

CONVICTIONS = Path(__file__).resolve().parents[2] / "convictions"


@pytest.fixture
async def session(tmp_path):
    db_path = tmp_path / "test.sqlite"
    db.migrate(db_path)
    engine = db.make_engine(f"sqlite+aiosqlite:///{db_path.as_posix()}")
    factory = db.make_session_factory(engine)
    async with factory() as s:
        yield s
    await engine.dispose()


async def test_ingest_raises_on_missing_directory(session: AsyncSession, tmp_path):
    missing = tmp_path / "does-not-exist"
    with pytest.raises(IngestError, match="not a directory"):
        await ingest_corpus(session, missing)


async def test_ingest_raises_when_no_passages(session: AsyncSession, tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    (empty / "ignored.txt").write_text("not markdown")
    with pytest.raises(IngestError, match="no passages parsed"):
        await ingest_corpus(session, empty)


async def test_ingest_inserts_parsed_passages(session: AsyncSession, tmp_path):
    sample = tmp_path / "corpus"
    sample.mkdir()
    (sample / "doc.md").write_text(
        "# Sample\n\n*Updated: April 2026*\n\n## First\n\nbody one\n\n## Second\n\nbody two\n",
        encoding="utf-8",
    )
    report = await ingest_corpus(session, sample)
    assert report.documents == 1
    assert report.passages == 2
    assert report.orphans_deleted == 0
    assert "doc#first" in await passages_repo.all_ids(session)


async def test_ingest_deletes_orphans_on_reingest(session: AsyncSession, tmp_path):
    sample = tmp_path / "corpus"
    sample.mkdir()
    md = sample / "doc.md"
    md.write_text("# Sample\n\n## First\n\nbody\n\n## Second\n\nmore\n", encoding="utf-8")

    first = await ingest_corpus(session, sample)
    assert first.passages == 2
    assert first.orphans_deleted == 0

    md.write_text(
        "# Sample\n\n## First\n\nbody\n\n## Second Renamed\n\nmore\n",
        encoding="utf-8",
    )
    second = await ingest_corpus(session, sample)
    assert second.passages == 2
    assert second.orphans_deleted == 1
    assert await passages_repo.all_ids(session) == {"doc#first", "doc#second-renamed"}


@pytest.mark.skipif(not CONVICTIONS.is_dir(), reason="corpus not found")
async def test_ingest_real_corpus(session: AsyncSession):
    report = await ingest_corpus(session, CONVICTIONS)
    assert report.documents == 30
    assert report.passages == 423
    assert report.orphans_deleted == 0
