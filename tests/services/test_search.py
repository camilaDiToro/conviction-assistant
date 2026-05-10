"""Unit tests for app/services/search.py — normalization, snippet, BM25Index lifecycle."""

from datetime import date

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import db
from app.repositories import passages as passages_repo
from app.schemas import Passage
from app.services.search import BM25Index, _make_snippet, _normalize


@pytest.fixture
async def session(tmp_path):
    db_path = tmp_path / "test.sqlite"
    db.migrate(db_path)
    engine = db.make_engine(f"sqlite+aiosqlite:///{db_path.as_posix()}")
    factory = db.make_session_factory(engine)
    async with factory() as s:
        yield s
    await engine.dispose()


def _passage(slug: str, doc: str, head: str, *, text: str, updated=None) -> Passage:
    title = doc.replace("_", " ").title()
    return Passage(
        id=f"{doc}#{slug}",
        document_id=doc,
        document_title=title,
        heading=head,
        heading_path=[title, head],
        text=text,
        document_updated=updated,
    )


# ---- _normalize ----


def test_normalize_strips_diacritics_for_pt():
    assert _normalize("tributação") == "tributacao"
    assert _normalize("Atualização Periódica") == "atualizacao periodica"


def test_normalize_strips_diacritics_for_es():
    assert _normalize("¿Cómo se calculan?") == "¿como se calculan?"


def test_normalize_lowercases():
    assert _normalize("CDB FGC") == "cdb fgc"


def test_normalize_collapses_whitespace():
    assert _normalize("  foo\t\n  bar   baz  ") == "foo bar baz"


def test_normalize_empty_or_whitespace_only():
    assert _normalize("") == ""
    assert _normalize("   \n\t  ") == ""


# ---- _make_snippet ----


def test_make_snippet_returns_full_text_under_max():
    assert _make_snippet("short text", max_chars=200) == "short text"


def test_make_snippet_truncates_at_word_boundary():
    text = "a" * 50 + " " + "b" * 50 + " " + "c" * 200
    snip = _make_snippet(text, max_chars=120)
    assert snip.endswith("…")
    assert len(snip) <= 121
    assert " " in snip  # cut at a word boundary


def test_make_snippet_collapses_internal_whitespace():
    assert _make_snippet("foo\n\n   bar", max_chars=200) == "foo bar"


# ---- BM25Index lifecycle ----


async def test_index_search_on_empty_returns_empty(session: AsyncSession):
    idx = BM25Index()
    await idx.build(session)
    assert idx.search("anything", k=5) == []


async def test_index_finds_literal_match(session: AsyncSession):
    items = [
        _passage("a", "doc_a", "FGC e CDB", text="O FGC garante até R$250 mil por CPF."),
        _passage("b", "doc_b", "Outro", text="Texto irrelevante sobre fundos imobiliários."),
        _passage("c", "doc_c", "Mais", text="Renda variável e ações."),
    ]
    async with session.begin():
        await passages_repo.upsert_many(session, items)

    idx = BM25Index()
    await idx.build(session)

    hits = idx.search("FGC garantia CDB", k=2)
    assert hits, "expected at least one hit"
    top, _ = hits[0]
    assert top.id == "doc_a#a"


async def test_index_accent_strip_recall(session: AsyncSession):
    """Query without diacritics still hits a passage with diacritics."""
    items = [
        _passage(
            "tax",
            "cdb",
            "Tributação",
            text="A tributação dos CDBs segue a tabela regressiva do IR.",
            updated=date(2026, 4, 1),
        ),
    ]
    async with session.begin():
        await passages_repo.upsert_many(session, items)

    idx = BM25Index()
    await idx.build(session)

    hits = idx.search("tributacao tabela regressiva", k=1)
    assert hits, "accent-stripped query should still match accented passage"
    assert hits[0][0].id == "cdb#tax"


async def test_index_rebuild_picks_up_new_passages(session: AsyncSession):
    idx = BM25Index()
    await idx.build(session)
    assert idx.search("anything", k=5) == []
    # build() leaves the session in an autobegun read transaction; close it
    # before opening an explicit write transaction.
    await session.commit()

    async with session.begin():
        await passages_repo.upsert_many(
            session, [_passage("x", "doc", "Heading", text="unique-token-zorgon body")]
        )
    await idx.rebuild(session)

    hits = idx.search("zorgon", k=5)
    assert hits and hits[0][0].id == "doc#x"


async def test_index_idempotent_double_build(session: AsyncSession):
    async with session.begin():
        await passages_repo.upsert_many(
            session, [_passage("x", "doc", "H", text="content alpha beta")]
        )
    idx = BM25Index()
    await idx.build(session)
    await session.commit()  # close autobegun read txn from build()
    await idx.build(session)  # second build must not corrupt state
    assert idx.search("alpha", k=1)[0][0].id == "doc#x"


async def test_index_search_k_capped_at_corpus_size(session: AsyncSession):
    async with session.begin():
        await passages_repo.upsert_many(
            session,
            [
                _passage("a", "doc", "A", text="alpha"),
                _passage("b", "doc", "B", text="beta"),
            ],
        )
    idx = BM25Index()
    await idx.build(session)

    hits = idx.search("alpha beta", k=50)
    assert len(hits) == 2
