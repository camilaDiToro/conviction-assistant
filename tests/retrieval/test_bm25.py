"""Unit tests for app/retrieval/bm25.py — normalization and BM25Retriever lifecycle.

Contract-level lifecycle tests (unbuilt search returns [], rebuild idempotent)
live in `test_protocol_conformance.py` and run against every registered
retriever. This file holds BM25-specific behavior: accent-strip recall, rebuild
picking up new passages, k-cap at corpus size.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import db
from app.repositories import passages as passages_repo
from app.retrieval.bm25 import BM25Retriever, _normalize
from app.schemas import Passage


@pytest.fixture
async def session(tmp_path):
    db_path = tmp_path / "test.sqlite"
    db.migrate(db_path)
    engine = db.make_engine(f"sqlite+aiosqlite:///{db_path.as_posix()}")
    factory = db.make_session_factory(engine)
    async with factory() as s:
        yield s
    await engine.dispose()


def _passage(slug: str, doc: str, head: str, *, text: str) -> Passage:
    title = doc.replace("_", " ").title()
    return Passage(
        id=f"{doc}#{slug}",
        document_id=doc,
        document_title=title,
        heading=head,
        heading_path=[title, head],
        text=text,
    )


# ---- _normalize ----


def test_normalize_strips_diacritics_for_pt():
    assert _normalize("tributação") == "tributacao"
    assert _normalize("Atualização Periódica") == "atualizacao periodica"


def test_normalize_strips_diacritics_for_es():
    assert _normalize("¿Cómo se calculan?") == "¿como se calculan?"


# ---- BM25Retriever lifecycle ----


async def test_index_finds_literal_match(session: AsyncSession):
    items = [
        _passage("a", "doc_a", "FGC e CDB", text="O FGC garante até R$250 mil por CPF."),
        _passage("b", "doc_b", "Outro", text="Texto irrelevante sobre fundos imobiliários."),
        _passage("c", "doc_c", "Mais", text="Renda variável e ações."),
    ]
    async with session.begin():
        await passages_repo.upsert_many(session, items)

    idx = BM25Retriever()
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
        ),
    ]
    async with session.begin():
        await passages_repo.upsert_many(session, items)

    idx = BM25Retriever()
    await idx.build(session)

    hits = idx.search("tributacao tabela regressiva", k=1)
    assert hits, "accent-stripped query should still match accented passage"
    assert hits[0][0].id == "cdb#tax"


async def test_index_rebuild_picks_up_new_passages(session: AsyncSession):
    idx = BM25Retriever()
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


async def test_index_search_k_capped_at_corpus_size(session: AsyncSession):
    async with session.begin():
        await passages_repo.upsert_many(
            session,
            [
                _passage("a", "doc", "A", text="alpha"),
                _passage("b", "doc", "B", text="beta"),
            ],
        )
    idx = BM25Retriever()
    await idx.build(session)

    hits = idx.search("alpha beta", k=50)
    assert len(hits) == 2
