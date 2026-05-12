"""Tests for the offset resolver.

Tested through the public entry point `resolve_answer`. One test per
outcome (anchored + 3 failure reasons), one for order preservation, one
regression guard for "no smart-quote normalization", and a property
test asserting any text slice anchors back to the same offsets.
"""

import random

from app.agent.resolver import resolve_answer
from app.agent.schemas import AnswerOutput, Citation
from app.schemas.passage import Passage


def _passage(text: str = "alpha bravo charlie", passage_id: str = "docA#sec") -> Passage:
    return Passage(
        id=passage_id,
        document_id=passage_id.split("#")[0],
        document_title="Doc",
        heading=passage_id.split("#", 1)[-1],
        heading_path=[passage_id.split("#", 1)[-1]],
        text=text,
    )


def _answer(*citations: Citation) -> AnswerOutput:
    return AnswerOutput(
        answer="x",
        citations=list(citations),
        general_knowledge_used=False,
        general_knowledge_section=None,
        out_of_scope=False,
    )


def test_anchored_entry_carries_provenance_and_offsets() -> None:
    p = _passage()
    a = _answer(Citation(passage_id=p.id, quote="bravo"))
    e = resolve_answer(a, {p.id: p}).entries[0]
    assert e.failure_reason is None
    assert e.passage_id == p.id
    assert e.document_id == p.document_id
    assert e.document_title == p.document_title
    assert e.heading_path == p.heading_path
    assert e.passage_text == p.text
    assert p.text[e.start : e.end] == "bravo"


def test_missing_passage_yields_passage_not_found() -> None:
    a = _answer(Citation(passage_id="missing#x", quote="foo"))
    e = resolve_answer(a, {}).entries[0]
    assert e.failure_reason == "passage_not_found"
    assert e.passage_text is None


def test_non_substring_quote_yields_offset_not_found() -> None:
    p = _passage()
    a = _answer(Citation(passage_id=p.id, quote="not a substring"))
    e = resolve_answer(a, {p.id: p}).entries[0]
    assert e.failure_reason == "offset_not_found"
    assert e.passage_text == p.text  # provenance survives


def test_empty_quote_yields_empty_quote_reason() -> None:
    a = _answer(Citation(passage_id="docA#sec", quote=""))
    e = resolve_answer(a, {}).entries[0]
    assert e.failure_reason == "empty_quote"


def test_cosmetic_diffs_fold_for_match() -> None:
    """Smart quotes, en/em dash and NBSP fold to ASCII before substring
    search. Offsets still index the original passage so the slice is
    cosmetically the passage's version, not the model's."""
    p = _passage(text='A position called "core" — described.')
    a = _answer(Citation(passage_id=p.id, quote="“core” – described"))
    e = resolve_answer(a, {p.id: p}).entries[0]
    assert e.failure_reason is None
    assert p.text[e.start : e.end] == '"core" — described'


def test_nbsp_in_passage_folds_to_space_in_quote() -> None:
    p = _passage(text="Tesouro IPCA+ 2027")
    a = _answer(Citation(passage_id=p.id, quote="Tesouro IPCA+ 2027"))
    e = resolve_answer(a, {p.id: p}).entries[0]
    assert e.failure_reason is None
    assert p.text[e.start : e.end] == "Tesouro IPCA+ 2027"


def test_preserves_citation_order_on_partial_failure() -> None:
    p = _passage()
    a = _answer(
        Citation(passage_id=p.id, quote="alpha"),
        Citation(passage_id=p.id, quote="not a substring"),
        Citation(passage_id=p.id, quote="charlie"),
    )
    result = resolve_answer(a, {p.id: p})
    assert [e.failure_reason for e in result.entries] == [None, "offset_not_found", None]


def test_any_text_slice_anchors() -> None:
    rng = random.Random(20260510)
    text = (
        "Em renda fixa, a tributação segue a tabela regressiva de IR — "
        "começando em 22.5% e caindo para 15% após 720 dias. CDB é o "
        "exemplo típico desta classe de ativo. Para LCI / LCA, há "
        "isenção pessoa física."
    )
    p = _passage(text=text)
    for _ in range(200):
        a = rng.randrange(0, len(text))
        b = rng.randrange(a + 1, len(text) + 1)
        slice_ = text[a:b]
        if not slice_.strip():
            continue
        ans = _answer(Citation(passage_id=p.id, quote=slice_))
        e = resolve_answer(ans, {p.id: p}).entries[0]
        assert e.failure_reason is None, f"slice [{a}:{b}] {slice_!r} did not anchor"
        assert text[e.start : e.end] == slice_
