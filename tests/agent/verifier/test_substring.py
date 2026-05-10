"""Tests for the substring verifier in app/agent/verifier/substring.py.

Covers the golden table from ROADMAP B8 acceptance plus a property
test: any random ``passage.text[a:b]`` slice (with ``a < b``) verifies
true against the right ``passage_id``. The point of the property test
is to defend against accidentally introducing a normalization rule
that changes content rather than cosmetics.
"""

import random
from datetime import date

from app.agent.schemas import AnswerOutput, Citation
from app.agent.verifier.normalize import normalize
from app.agent.verifier.substring import (
    VerificationResult,
    VerifiedCitation,
    verify_answer,
    verify_citation,
)
from app.schemas.passage import Passage

# ---- helpers --------------------------------------------------------


def _passage(
    passage_id: str = "doc#sec",
    text: str = "CDBs follow the tabela regressiva de IR.",
) -> Passage:
    return Passage(
        id=passage_id,
        document_id=passage_id.split("#")[0],
        document_title="Doc",
        heading="sec",
        heading_path=["sec"],
        text=text,
        document_updated=date(2026, 4, 1),
    )


def _answer(*citations: Citation) -> AnswerOutput:
    return AnswerOutput(
        answer="example answer",
        citations=list(citations),
        general_knowledge_used=False,
        general_knowledge_section=None,
        out_of_scope=False,
    )


# ---- verify_citation: golden table ---------------------------------


def test_matching_quote_passes() -> None:
    assert verify_citation("tabela regressiva", "CDBs follow the tabela regressiva de IR.")


def test_paraphrase_fails() -> None:
    assert not verify_citation(
        "regressive table for fixed income", "CDBs follow the tabela regressiva de IR."
    )


def test_empty_quote_fails() -> None:
    assert not verify_citation("", "any passage text")
    assert not verify_citation("   ", "any passage text")


def test_smart_quote_mismatch_passes_after_normalization() -> None:
    # The quote uses a smart double-quote; the passage uses ASCII quotes.
    # Normalization folds both to ASCII, so the substring matches.
    passage_text = 'A position called "core" is described.'
    quote = "“core”"
    assert verify_citation(quote, passage_text)


def test_nbsp_vs_space_passes() -> None:
    # The model emitted a quote with a regular space; the passage has NBSP
    # (or vice versa). After collapse, they match.
    passage_text = "CDB tributação é regressiva."
    assert verify_citation("CDB tributação", passage_text)


def test_pt_diacritics_round_trip() -> None:
    passage_text = "Em renda fixa, a tributação é regressiva e diminui com o tempo."
    assert verify_citation("tributação é regressiva", passage_text)


def test_em_dash_normalization_match() -> None:
    passage_text = "CDB — a tributação é regressiva."
    assert verify_citation("CDB - a tributação", passage_text)


def test_quote_must_be_substring_not_subset_of_words() -> None:
    # "tabela IR" is a subset of words but not a substring.
    passage_text = "CDBs follow the tabela regressiva de IR."
    assert not verify_citation("tabela IR", passage_text)


# ---- verify_answer: per-citation outcomes --------------------------


def test_verify_answer_pass_emits_verified_citation_with_provenance() -> None:
    p = _passage("docA#sec1", "alpha bravo charlie")
    a = _answer(Citation(passage_id="docA#sec1", quote="bravo"))
    result = verify_answer(a, {p.id: p})
    assert result.all_passed
    assert len(result.verified) == 1
    vc = result.verified[0]
    assert isinstance(vc, VerifiedCitation)
    assert vc.passage_id == p.id
    assert vc.document_id == p.document_id
    assert vc.document_title == p.document_title
    assert vc.heading_path == p.heading_path
    assert vc.document_updated == p.document_updated
    assert vc.quote == "bravo"


def test_verify_answer_passage_not_in_map_records_passage_not_found() -> None:
    a = _answer(Citation(passage_id="missing#x", quote="foo"))
    result = verify_answer(a, {})
    assert not result.all_passed
    assert len(result.failures) == 1
    f = result.failures[0]
    assert f.reason == "passage_not_found"
    assert f.passage_id == "missing#x"
    assert f.index == 0


def test_verify_answer_cross_passage_quote_fails() -> None:
    """Quote text matches one passage but is attributed to a different one."""
    pA = _passage("docA#sec", "alpha quote text here")
    pB = _passage("docB#sec", "completely different content")
    a = _answer(Citation(passage_id="docB#sec", quote="alpha quote"))
    result = verify_answer(a, {pA.id: pA, pB.id: pB})
    assert not result.all_passed
    assert result.failures[0].reason == "substring_not_found"


def test_verify_answer_empty_quote_records_empty_quote_reason() -> None:
    a = _answer(Citation(passage_id="docA#sec", quote=""))
    result = verify_answer(a, {})
    assert not result.all_passed
    assert result.failures[0].reason == "empty_quote"


def test_verify_answer_partial_pass_preserves_index() -> None:
    p = _passage("docA#sec", "alpha bravo charlie")
    a = _answer(
        Citation(passage_id="docA#sec", quote="alpha"),
        Citation(passage_id="docA#sec", quote="not a substring"),
        Citation(passage_id="docA#sec", quote="charlie"),
    )
    result = verify_answer(a, {p.id: p})
    assert len(result.verified) == 2
    assert [vc.quote for vc in result.verified] == ["alpha", "charlie"]
    assert len(result.failures) == 1
    assert result.failures[0].index == 1
    assert result.failures[0].reason == "substring_not_found"


def test_verify_answer_no_citations_passes_trivially() -> None:
    a = _answer()
    result = verify_answer(a, {})
    assert isinstance(result, VerificationResult)
    assert result.all_passed
    assert result.verified == []
    assert result.failures == []


# ---- property: any text[a:b] verifies true -------------------------


def test_any_substring_slice_verifies_true() -> None:
    """For any (a, b) with 0 <= a < b <= len(text), the slice
    ``text[a:b]`` must verify true against the passage holding that text.
    Defends against future normalization changes that drop content.
    """
    rng = random.Random(20260510)
    text = (
        "Em renda fixa, a tributação segue a tabela regressiva de IR — começando "
        "em 22.5% e caindo para 15% após 720 dias. “CDB” é o exemplo "
        "típico desta classe de ativo. Para LCI / LCA, há isenção pessoa física."
    )
    p = _passage("docA#sec", text)

    for _ in range(200):
        a = rng.randrange(0, len(text))
        b = rng.randrange(a + 1, len(text) + 1)
        slice_ = text[a:b]
        # Skip slices that normalize to empty (pure whitespace runs).
        if not normalize(slice_):
            continue
        ans = _answer(Citation(passage_id=p.id, quote=slice_))
        result = verify_answer(ans, {p.id: p})
        assert result.all_passed, (
            f"slice [{a}:{b}] {slice_!r} failed; "
            f"failures={[f.model_dump() for f in result.failures]}"
        )
