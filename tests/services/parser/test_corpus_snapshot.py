"""Pin the parser's output against the real corpus.

If any of these constants changes, it should be a deliberate decision —
ID drift would silently break previously-verified citations.
"""

from pathlib import Path

import pytest

from app.services.parser import parse_corpus

CONVICTIONS = Path(__file__).resolve().parents[3] / "convictions"

EXPECTED_DOC_COUNT = 30
MIN_PASSAGES_PER_DOC = 3
EXPECTED_UNDATED_DOCS = {
    "b3_trading_mechanics",
    "bdrs_investing_guide",
    "complete_guide_brazilian_derivatives",
    "corporate_governance_levels_b3",
    "cra_cri_agribusiness_bonds",
    "currency_exposure_strategies",
    "debentures_incentivadas_analysis",
    "dividend_aristocrats_brazil",
    "etfs_brasileiros_guia",
    "guia_completo_tributacao_investimentos",
    "macroeconomic_factors_brazilian_markets",
    "real_estate_development_funds",
    "tesouro_direto_estrategias_avancadas",
}


@pytest.fixture(scope="module")
def passages():
    if not CONVICTIONS.is_dir():
        pytest.skip(f"corpus not found: {CONVICTIONS}")
    return parse_corpus(CONVICTIONS)


def test_corpus_shape(passages) -> None:
    by_doc = {p.document_id: p.document_updated for p in passages}
    ids = [p.id for p in passages]

    assert len(by_doc) == EXPECTED_DOC_COUNT
    assert len(passages) >= EXPECTED_DOC_COUNT * MIN_PASSAGES_PER_DOC
    assert {d for d, dt in by_doc.items() if dt is None} == EXPECTED_UNDATED_DOCS
    assert len(ids) == len(set(ids))


def test_known_passage_ids_present(passages) -> None:
    ids = {p.id for p in passages}
    assert "cdbs_quick_guide#o-que-e-um-cdb" in ids
    assert "b3_trading_mechanics#executive-summary" in ids
