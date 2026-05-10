"""Tests for the offset resolver in app/agent/resolver/substring.py.

Two layers:

1. ``resolve_citation`` — pure substring search; returns half-open
   ``(start, end)`` offsets or ``None``.
2. ``resolve_answer`` — wraps the per-citation resolver, producing an
   :class:`OffsetResolution` whose entries align one-to-one with the
   model's ``output.citations``.

A property test asserts the resolver round-trips any random
``passage.text[a:b]`` slice — defends against future changes that drop
content from the matching path.
"""

import random

from app.agent.resolver import (
    CitationResolution,
    OffsetResolution,
    resolve_answer,
    resolve_citation,
)
from app.agent.schemas import AnswerOutput, Citation
from app.schemas.passage import Passage


def _passage(
    passage_id: str = "doc#sec",
    text: str = "CDBs follow the tabela regressiva de IR.",
) -> Passage:
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
        answer="example answer",
        citations=list(citations),
        general_knowledge_used=False,
        general_knowledge_section=None,
        out_of_scope=False,
    )


# ---- resolve_citation: per-quote outcomes --------------------------


def test_matching_quote_returns_half_open_offsets() -> None:
    passage = "CDBs follow the tabela regressiva de IR."
    result = resolve_citation("tabela regressiva", passage)
    assert result is not None
    start, end = result
    assert passage[start:end] == "tabela regressiva"


def test_paraphrase_returns_none() -> None:
    assert resolve_citation(
        "regressive table for fixed income", "CDBs follow the tabela regressiva de IR."
    ) is None


def test_empty_quote_returns_none() -> None:
    assert resolve_citation("", "any passage text") is None


def test_quote_with_smart_quotes_does_not_anchor_to_ascii_source() -> None:
    """Deliberate: the resolver is literal — cosmetic mismatches lose
    their highlight (the citation survives with offsets None upstream)."""
    assert resolve_citation('“core”', 'A position called "core" is described.') is None


def test_quote_must_be_substring_not_subset_of_words() -> None:
    # "tabela IR" is a subset of words but not a substring.
    assert resolve_citation("tabela IR", "CDBs follow the tabela regressiva de IR.") is None


# ---- resolve_answer: per-citation outcomes --------------------------


def test_resolve_answer_pass_emits_anchored_entry() -> None:
    p = _passage("docA#sec1", "alpha bravo charlie")
    a = _answer(Citation(passage_id="docA#sec1", quote="bravo"))
    result = resolve_answer(a, {p.id: p})
    assert isinstance(result, OffsetResolution)
    assert result.all_anchored
    assert len(result.entries) == 1
    e = result.entries[0]
    assert isinstance(e, CitationResolution)
    assert e.passage_id == p.id
    assert e.document_id == p.document_id
    assert e.document_title == p.document_title
    assert e.heading_path == p.heading_path
    assert e.passage_text == p.text
    assert e.start == 6
    assert e.end == 11
    assert p.text[e.start:e.end] == "bravo"
    assert e.failure_reason is None


def test_resolve_answer_passage_not_in_map_records_passage_not_found() -> None:
    a = _answer(Citation(passage_id="missing#x", quote="foo"))
    result = resolve_answer(a, {})
    assert not result.all_anchored
    assert len(result.entries) == 1
    e = result.entries[0]
    assert e.failure_reason == "passage_not_found"
    assert e.passage_id == "missing#x"
    assert e.passage_text is None
    assert e.start is None and e.end is None


def test_resolve_answer_cross_passage_quote_yields_offset_not_found() -> None:
    """Quote text matches one passage but is attributed to a different one."""
    pA = _passage("docA#sec", "alpha quote text here")
    pB = _passage("docB#sec", "completely different content")
    a = _answer(Citation(passage_id="docB#sec", quote="alpha quote"))
    result = resolve_answer(a, {pA.id: pA, pB.id: pB})
    assert not result.all_anchored
    e = result.entries[0]
    assert e.failure_reason == "offset_not_found"
    # Passage provenance still carried so the UI can show pB without a highlight.
    assert e.passage_id == pB.id
    assert e.passage_text == pB.text


def test_resolve_answer_empty_quote_records_empty_quote_reason() -> None:
    a = _answer(Citation(passage_id="docA#sec", quote=""))
    result = resolve_answer(a, {})
    e = result.entries[0]
    assert e.failure_reason == "empty_quote"


def test_resolve_answer_preserves_order_on_partial_failure() -> None:
    p = _passage("docA#sec", "alpha bravo charlie")
    a = _answer(
        Citation(passage_id="docA#sec", quote="alpha"),
        Citation(passage_id="docA#sec", quote="not a substring"),
        Citation(passage_id="docA#sec", quote="charlie"),
    )
    result = resolve_answer(a, {p.id: p})
    assert [e.failure_reason for e in result.entries] == [
        None,
        "offset_not_found",
        None,
    ]
    assert p.text[result.entries[0].start : result.entries[0].end] == "alpha"
    assert p.text[result.entries[2].start : result.entries[2].end] == "charlie"


def test_resolve_answer_no_citations_returns_empty_entries() -> None:
    a = _answer()
    result = resolve_answer(a, {})
    assert result.all_anchored
    assert result.entries == []


# ---- property: any text[a:b] anchors ------------------------------


def test_any_substring_slice_anchors() -> None:
    """For any (a, b) with 0 <= a < b <= len(text), the slice
    ``text[a:b]`` must anchor to the same (a, b) offsets when handed
    back as a quote against the passage holding that text.
    """
    rng = random.Random(20260510)
    text = (
        "Em renda fixa, a tributação segue a tabela regressiva de IR — "
        "começando em 22.5% e caindo para 15% após 720 dias. CDB é o "
        "exemplo típico desta classe de ativo. Para LCI / LCA, há "
        "isenção pessoa física."
    )
    p = _passage("docA#sec", text)

    for _ in range(200):
        a = rng.randrange(0, len(text))
        b = rng.randrange(a + 1, len(text) + 1)
        slice_ = text[a:b]
        if not slice_.strip():
            continue
        ans = _answer(Citation(passage_id=p.id, quote=slice_))
        result = resolve_answer(ans, {p.id: p})
        e = result.entries[0]
        assert e.failure_reason is None, (
            f"slice [{a}:{b}] {slice_!r} unexpectedly unresolved: {e.model_dump()}"
        )
        # The resolver should find the FIRST occurrence — assert content
        # matches even if (start, end) is an earlier identical match.
        assert text[e.start : e.end] == slice_
