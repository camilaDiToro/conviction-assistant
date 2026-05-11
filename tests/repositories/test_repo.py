"""Async integration tests for the passage repository over a per-test SQLite."""

from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import db
from app.repositories import introspection
from app.repositories import passages as passages_repo
from app.schemas import Passage
from app.services.parser import parse_corpus

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


def _passage(slug, doc, head, text="...", title=None):
    title = title or doc.replace("_", " ").title()
    return Passage(
        id=f"{doc}#{slug}",
        document_id=doc,
        document_title=title,
        heading=head,
        heading_path=[title, head],
        text=text,
    )


# ---- repo functions ----


async def test_upsert_then_get_round_trip(session: AsyncSession):
    p = _passage("intro", "cdb_guide", "Intro", "what is a CDB")
    async with session.begin():
        n = await passages_repo.upsert_many(session, [p])
    assert n == 1
    got = await passages_repo.get(session, p.id)
    assert got == p


async def test_get_returns_none_for_unknown(session: AsyncSession):
    assert await passages_repo.get(session, "nope#missing") is None


async def test_upsert_many_handles_empty_input(session: AsyncSession):
    async with session.begin():
        n = await passages_repo.upsert_many(session, [])
    assert n == 0


async def test_list_documents_groups_per_document(session: AsyncSession):
    items = [
        _passage("a", "doc1", "A"),
        _passage("b", "doc1", "B"),
        _passage("c", "doc2", "C"),
    ]
    async with session.begin():
        await passages_repo.upsert_many(session, items)
    docs = {d.id: d for d in await passages_repo.list_documents(session, limit=30)}
    assert docs["doc1"].passage_count == 2
    assert docs["doc2"].passage_count == 1


async def test_get_document_summary_returns_one_doc(session: AsyncSession):
    items = [
        _passage("a", "doc1", "A"),
        _passage("b", "doc1", "B"),
        _passage("c", "doc2", "C"),
    ]
    async with session.begin():
        await passages_repo.upsert_many(session, items)
    summary = await passages_repo.get_document_summary(session, "doc2")
    assert summary is not None
    assert summary.id == "doc2"
    assert summary.passage_count == 1


async def test_get_document_summary_returns_none_for_unknown(session: AsyncSession):
    assert await passages_repo.get_document_summary(session, "ghost") is None


async def test_read_outline_preserves_insertion_order(session: AsyncSession):
    items = [
        _passage("first", "doc1", "First"),
        _passage("second", "doc1", "Second"),
        _passage("third", "doc1", "Third"),
    ]
    async with session.begin():
        await passages_repo.upsert_many(session, items)
    outline = await passages_repo.read_outline(session, "doc1")
    assert [h.heading for h in outline] == ["First", "Second", "Third"]
    assert [h.ordinal for h in outline] == [0, 1, 2]


async def test_idempotent_reingest(session: AsyncSession):
    items = [_passage("a", "doc1", "A"), _passage("b", "doc1", "B")]
    async with session.begin():
        await passages_repo.upsert_many(session, items)
    async with session.begin():
        await passages_repo.upsert_many(session, items)
    docs = await passages_repo.list_documents(session, limit=30)
    assert {d.passage_count for d in docs} == {2}


async def test_orphan_detection_and_delete(session: AsyncSession):
    async with session.begin():
        await passages_repo.upsert_many(
            session,
            [_passage("a", "doc1", "A"), _passage("b", "doc1", "B")],
        )
        existing = await passages_repo.all_ids(session)
        new = [_passage("a", "doc1", "A renamed", "new text")]
        orphans = existing - {p.id for p in new}
        await passages_repo.upsert_many(session, new)
        deleted = await passages_repo.delete_ids(session, orphans)
        assert deleted == 1
        assert await passages_repo.all_ids(session) == {"doc1#a"}


async def test_delete_ids_handles_empty_input(session: AsyncSession):
    async with session.begin():
        await passages_repo.upsert_many(session, [_passage("a", "doc1", "A")])
        deleted = await passages_repo.delete_ids(session, [])
    assert deleted == 0
    assert await passages_repo.all_ids(session) == {"doc1#a"}


async def test_heading_path_round_trips_unicode(session: AsyncSession):
    p = Passage(
        id="doc#x",
        document_id="doc",
        document_title="Doc",
        heading="Tributação",
        heading_path=["Doc", "Tributação", "Tabela Regressiva — IR"],
        text="...",
    )
    async with session.begin():
        await passages_repo.upsert_many(session, [p])
    got = await passages_repo.get(session, p.id)
    assert got is not None
    assert got.heading_path == ["Doc", "Tributação", "Tabela Regressiva — IR"]


# ---- migration / bootstrap ----


async def test_migrate_creates_schema(session: AsyncSession):
    """Migrate-then-use must work end-to-end."""
    assert "passages" in await introspection.list_tables(session)
    assert "audit_log" in await introspection.list_tables(session)


async def test_migrate_is_idempotent(tmp_path):
    db_path = tmp_path / "twice.sqlite"
    db.migrate(db_path)
    db.migrate(db_path)  # second call must be a no-op
    engine = db.make_engine(f"sqlite+aiosqlite:///{db_path.as_posix()}")
    try:
        factory = db.make_session_factory(engine)
        async with factory() as s:
            ids = await passages_repo.all_ids(s)
        assert ids == set()
    finally:
        await engine.dispose()


# ---- end-to-end with the real corpus ----


@pytest.mark.skipif(not CONVICTIONS.is_dir(), reason="corpus not found")
async def test_end_to_end_real_corpus(tmp_path):
    parsed = parse_corpus(CONVICTIONS)
    db_path = tmp_path / "real.sqlite"
    db.migrate(db_path)
    engine = db.make_engine(f"sqlite+aiosqlite:///{db_path.as_posix()}")
    try:
        factory = db.make_session_factory(engine)
        async with factory() as s:
            async with s.begin():
                n = await passages_repo.upsert_many(s, parsed)
            assert n == len(parsed)
            docs = await passages_repo.list_documents(s, limit=100)
            assert len(docs) == 30
            cdb = await passages_repo.get(s, "cdbs_quick_guide#o-que-e-um-cdb")
            assert cdb is not None
            assert cdb.document_id == "cdbs_quick_guide"
    finally:
        await engine.dispose()
