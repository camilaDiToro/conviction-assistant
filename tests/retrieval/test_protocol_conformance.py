"""Parametrized conformance suite for every registered :class:`Retriever`.

Today only ``bm25`` is registered; the parametrization is the seam for
tomorrow — when ``hybrid`` (or another strategy) lands, every test
here runs against both with no copy-paste.

The contract these tests pin:

- A fresh retriever returns ``[]`` from ``search`` before ``build`` is
  called (no AttributeError, no half-state).
- After ``build`` against a known passage set, ``search`` for a literal
  query returns at most ``k`` results, ordered by descending score.
- ``search`` for a query with no matching tokens returns a list (empty
  or low-scoring; either is contract-conformant).
- ``rebuild`` against an unchanged corpus is idempotent.

Tests use a tmp-path SQLite + the parser's :func:`ingest_corpus` to
populate a known passage set. Module-scoped because parsing/indexing
is non-trivial; conformance tests pay the setup once per retriever.
"""

from collections.abc import AsyncIterator
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import db
from app.retrieval import Retriever, available_retrievers, get_retriever

# A tiny synthetic corpus written into a tmp markdown file. Real
# convictions/ would inflate setup time; the contract doesn't care
# about content, only behavior.
_FIXTURE_MD = """# Sample doc

## Tributação CDB

CDBs follow the tabela regressiva de IR.

## LCI overview

LCI are tax-exempt fixed-income securities.
"""


@pytest_asyncio.fixture(scope="module")
async def populated_session(
    tmp_path_factory: pytest.TempPathFactory,
) -> AsyncIterator[AsyncSession]:
    """Spin up a tmp-path SQLite, ingest the synthetic corpus, yield a session."""
    tmp_path = tmp_path_factory.mktemp("retriever_conformance")
    convictions_dir = tmp_path / "convictions"
    convictions_dir.mkdir()
    (convictions_dir / "sample.md").write_text(_FIXTURE_MD, encoding="utf-8")

    db_path = tmp_path / "conformance.sqlite"
    db.migrate(db_path)
    engine = db.make_engine(f"sqlite+aiosqlite:///{db_path.as_posix()}")
    factory = db.make_session_factory(engine)

    from app.services.ingest import ingest_corpus

    async with factory() as session:
        await ingest_corpus(session, Path(convictions_dir))
        yield session

    await engine.dispose()


@pytest.fixture(params=available_retrievers())
def retriever_name(request: pytest.FixtureRequest) -> str:
    return request.param


def test_unbuilt_search_returns_empty(retriever_name: str) -> None:
    """Before ``build`` runs, ``search`` must not crash; it returns ``[]``."""
    retriever: Retriever = get_retriever(retriever_name)
    assert retriever.search("anything", k=5) == []


@pytest.mark.asyncio
async def test_build_then_search_returns_k_or_fewer_results(
    retriever_name: str,
    populated_session: AsyncSession,
) -> None:
    retriever: Retriever = get_retriever(retriever_name)
    await retriever.build(populated_session)

    hits = retriever.search("CDB tabela regressiva", k=5)
    assert hits, "literal query should return at least one hit"
    assert len(hits) <= 5
    # Scores are descending.
    scores = [score for _, score in hits]
    assert scores == sorted(scores, reverse=True)


@pytest.mark.asyncio
async def test_rebuild_is_idempotent(
    retriever_name: str,
    populated_session: AsyncSession,
) -> None:
    """``rebuild`` against the same corpus produces the same hits."""
    retriever: Retriever = get_retriever(retriever_name)
    await retriever.build(populated_session)
    before = retriever.search("CDB", k=5)
    await retriever.rebuild(populated_session)
    after = retriever.search("CDB", k=5)
    assert [p.id for p, _ in before] == [p.id for p, _ in after]
