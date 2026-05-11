"""Pin the parser's output against the real corpus.

If any of these constants changes, it should be a deliberate decision —
ID drift would silently break previously-verified citations.
"""

from collections import Counter
from pathlib import Path

import pytest

from app.services.parser import parse_corpus

CONVICTIONS = Path(__file__).resolve().parents[3] / "convictions"

EXPECTED_DOC_COUNT = 30
MIN_PASSAGES_PER_DOC = 3


@pytest.fixture(scope="module")
def passages():
    if not CONVICTIONS.is_dir():
        pytest.skip(f"corpus not found: {CONVICTIONS}")
    return parse_corpus(CONVICTIONS)


def test_corpus_shape(passages) -> None:
    doc_ids = {p.document_id for p in passages}
    ids = [p.id for p in passages]

    assert len(doc_ids) == EXPECTED_DOC_COUNT
    assert len(ids) == len(set(ids))

    by_doc = Counter(p.document_id for p in passages)
    thin = [d for d, n in by_doc.items() if n < MIN_PASSAGES_PER_DOC]
    assert not thin, f"docs with fewer than {MIN_PASSAGES_PER_DOC} passages: {thin}"


def test_known_passage_ids_present(passages) -> None:
    ids = {p.id for p in passages}
    assert "cdbs_quick_guide#o-que-e-um-cdb" in ids
    assert "b3_trading_mechanics#executive-summary" in ids
