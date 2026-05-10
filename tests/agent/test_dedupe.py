"""Unit tests for app.agent.dedupe.dedupe_citations."""

from app.agent.dedupe import dedupe_citations
from app.agent.schemas import AnswerOutput, Citation


def _make_output(citations: list[Citation], answer: str) -> AnswerOutput:
    return AnswerOutput(
        answer=answer,
        citations=citations,
        general_knowledge_used=False,
        general_knowledge_section=None,
        out_of_scope=False,
    )


def test_dedupe_collapses_duplicate_passage_ids_and_remaps_markers() -> None:
    output = _make_output(
        citations=[
            Citation(passage_id="doc#a", quote="quote A1"),
            Citation(passage_id="doc#b", quote="quote B"),
            Citation(passage_id="doc#a", quote="quote A2"),
        ],
        answer="claim A [1] and claim B [2] and claim C [3]",
    )

    result = dedupe_citations(output)

    assert [c.passage_id for c in result.citations] == ["doc#a", "doc#b"]
    # Kept the first quote per passage; A2 was dropped.
    assert result.citations[0].quote == "quote A1"
    assert result.citations[1].quote == "quote B"
    assert result.answer == "claim A [1] and claim B [2] and claim C [1]"


def test_dedupe_is_a_noop_when_all_citations_are_unique() -> None:
    output = _make_output(
        citations=[
            Citation(passage_id="doc#a", quote="qa"),
            Citation(passage_id="doc#b", quote="qb"),
        ],
        answer="alpha [1] beta [2]",
    )

    result = dedupe_citations(output)

    assert result is output  # same object — no rewrite happened


def test_dedupe_leaves_out_of_range_markers_untouched() -> None:
    output = _make_output(
        citations=[
            Citation(passage_id="doc#a", quote="qa"),
            Citation(passage_id="doc#a", quote="qa2"),
        ],
        # [9] has no corresponding citation; [0] is invalid; both must be left alone.
        answer="claim A [1] and bracketed number [9] and zero [0]",
    )

    result = dedupe_citations(output)

    assert len(result.citations) == 1
    assert result.answer == "claim A [1] and bracketed number [9] and zero [0]"


def test_dedupe_handles_empty_citations() -> None:
    output = _make_output(citations=[], answer="no citations here")
    result = dedupe_citations(output)
    assert result is output
