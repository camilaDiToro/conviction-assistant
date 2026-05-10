"""Pure-function tests for the three B5 read-only tools."""

from datetime import date

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.tools import (
    TOOLS,
    ToolContext,
    list_documents,
    read_document_outline,
    read_passage,
)
from app.config import db
from app.errors import DocumentNotFoundError, PassageNotFoundError
from app.repositories import passages as passages_repo
from app.retrieval.bm25 import BM25Retriever
from app.schemas import DocSummary, DocumentOutline, Passage


@pytest.fixture
async def session(tmp_path):
    db_path = tmp_path / "test.sqlite"
    db.migrate(db_path)
    engine = db.make_engine(f"sqlite+aiosqlite:///{db_path.as_posix()}")
    factory = db.make_session_factory(engine)
    async with factory() as s:
        yield s
    await engine.dispose()


def _passage(slug: str, doc: str, head: str, *, text: str = "...", updated=None, title=None):
    title = title or doc.replace("_", " ").title()
    return Passage(
        id=f"{doc}#{slug}",
        document_id=doc,
        document_title=title,
        heading=head,
        heading_path=[title, head],
        text=text,
        document_updated=updated,
    )


# ---- list_documents ----


async def test_list_documents_returns_doc_summaries(session: AsyncSession):
    items = [
        _passage("a", "doc_a", "A1"),
        _passage("b", "doc_a", "A2"),
        _passage("c", "doc_b", "B1", updated=date(2026, 4, 1)),
        _passage("d", "doc_c", "C1"),
    ]
    async with session.begin():
        await passages_repo.upsert_many(session, items)
    ctx = ToolContext(session=session, retriever=BM25Retriever())

    result = await list_documents(ctx)

    assert all(isinstance(d, DocSummary) for d in result)
    assert [d.id for d in result] == ["doc_a", "doc_b", "doc_c"]
    by_id = {d.id: d for d in result}
    assert by_id["doc_a"].passage_count == 2
    assert by_id["doc_a"].document_updated is None
    assert by_id["doc_b"].document_updated == date(2026, 4, 1)
    assert by_id["doc_c"].passage_count == 1


async def test_list_documents_on_empty_corpus_returns_empty(session: AsyncSession):
    ctx = ToolContext(session=session, retriever=BM25Retriever())
    result = await list_documents(ctx)
    assert result == []


# ---- read_document_outline ----


async def test_read_document_outline_returns_full_outline(session: AsyncSession):
    items = [
        _passage("intro", "cdb_guide", "Intro", updated=date(2026, 4, 1)),
        _passage("tax", "cdb_guide", "Tributação", updated=date(2026, 4, 1)),
        _passage("risk", "cdb_guide", "Risco", updated=date(2026, 4, 1)),
    ]
    async with session.begin():
        await passages_repo.upsert_many(session, items)
    ctx = ToolContext(session=session, retriever=BM25Retriever())

    outline = await read_document_outline(ctx, document_id="cdb_guide")

    assert isinstance(outline, DocumentOutline)
    assert outline.document_id == "cdb_guide"
    assert outline.document_title == "Cdb Guide"
    assert outline.document_updated == date(2026, 4, 1)
    assert outline.passage_count == 3
    assert [h.heading for h in outline.headings] == ["Intro", "Tributação", "Risco"]
    assert [h.ordinal for h in outline.headings] == [0, 1, 2]
    assert [h.passage_id for h in outline.headings] == [
        "cdb_guide#intro",
        "cdb_guide#tax",
        "cdb_guide#risk",
    ]


async def test_read_document_outline_unknown_id_raises(session: AsyncSession):
    ctx = ToolContext(session=session, retriever=BM25Retriever())
    with pytest.raises(DocumentNotFoundError) as excinfo:
        await read_document_outline(ctx, document_id="ghost")
    assert excinfo.value.document_id == "ghost"


async def test_read_document_outline_undated_doc(session: AsyncSession):
    async with session.begin():
        await passages_repo.upsert_many(
            session, [_passage("a", "undated", "A"), _passage("b", "undated", "B")]
        )
    ctx = ToolContext(session=session, retriever=BM25Retriever())

    outline = await read_document_outline(ctx, document_id="undated")

    assert outline.document_updated is None
    assert outline.passage_count == 2


# ---- read_passage ----


async def test_read_passage_returns_passages_in_input_order(session: AsyncSession):
    items = [
        _passage("a", "doc_x", "A", text="alpha", updated=date(2026, 4, 1)),
        _passage("b", "doc_x", "B", text="beta", updated=date(2026, 4, 1)),
    ]
    async with session.begin():
        await passages_repo.upsert_many(session, items)
    ctx = ToolContext(session=session, retriever=BM25Retriever())

    got = await read_passage(ctx, passage_ids=["doc_x#b", "doc_x#a"])

    assert [p.id for p in got] == ["doc_x#b", "doc_x#a"]
    assert [p.text for p in got] == ["beta", "alpha"]
    assert all(isinstance(p, Passage) for p in got)


async def test_read_passage_raises_on_any_missing_id(session: AsyncSession):
    async with session.begin():
        await passages_repo.upsert_many(session, [_passage("a", "doc_x", "A")])
    ctx = ToolContext(session=session, retriever=BM25Retriever())

    with pytest.raises(PassageNotFoundError) as excinfo:
        await read_passage(ctx, passage_ids=["doc_x#a", "doc_x#missing"])
    assert excinfo.value.passage_id == "doc_x#missing"


# ---- TOOLS registry / schema-shape sanity ----


def test_tools_registry_keys_match_definition_names():
    for name, entry in TOOLS.items():
        assert entry.definition.name == name


def test_tools_registry_has_all_four_tools():
    assert set(TOOLS.keys()) == {
        "list_documents",
        "read_document_outline",
        "search_convictions",
        "read_passage",
    }


def test_tool_parameter_schemas_satisfy_openai_strict_mode():
    """OpenAI strict mode demands every property in `required`,
    `additionalProperties: false`, and no `default` keys.
    """
    for name, entry in TOOLS.items():
        params = entry.definition.parameters
        assert params["type"] == "object", name
        assert params["additionalProperties"] is False, name
        properties = params.get("properties", {})
        required = params.get("required", [])
        assert set(required) == set(properties.keys()), name
        for prop_name, prop_schema in properties.items():
            assert "default" not in prop_schema, f"{name}.{prop_name}"


def test_tool_definitions_have_nontrivial_descriptions():
    """Tool descriptions are the LLM's only signal for tool choice; bare
    placeholders would silently degrade B8 prompt behavior.
    """
    for name, entry in TOOLS.items():
        assert len(entry.definition.description) >= 40, name
