"""Offset resolver: pure substring search over Citation + Passage.

Literal str.find — no smart-quote / NBSP / dash normalization. The
model copies its quote from read_passage (DB-verbatim), so cosmetic
diffs are rare; when they happen the citation surfaces without a
highlight. The agent loop's adapter (app.agent.audit.resolve_output)
loads passages and hands them in.
"""

from typing import TYPE_CHECKING, Any

from app.agent.resolver.base import CitationResolution, OffsetResolution
from app.schemas.passage import Passage

if TYPE_CHECKING:
    from app.agent.schemas import AnswerOutput, Citation


def resolve_citation(quote: str, passage_text: str) -> tuple[int, int] | None:
    """First (start, end) of `quote` in `passage_text`, or None if empty
    or not a substring. Half-open: passage_text[start:end] == quote."""
    if not quote:
        return None
    idx = passage_text.find(quote)
    if idx == -1:
        return None
    return idx, idx + len(quote)


def resolve_answer(
    answer: "AnswerOutput",
    passages: dict[str, Passage],
) -> OffsetResolution:
    """Resolve every citation against the passage map. Order preserved.

    Outcomes: empty quote → 'empty_quote'; passage_id missing →
    'passage_not_found'; non-substring quote → 'offset_not_found';
    match → anchored with (start, end). Caller populates the map
    (see app.agent.audit.resolve_output).
    """
    return OffsetResolution(
        entries=[_resolve_one(c, passages.get(c.passage_id)) for c in answer.citations]
    )


def _resolve_one(citation: "Citation", passage: Passage | None) -> CitationResolution:
    """Resolve one citation. Provenance comes from `passage` if present,
    else nullified — independent of the outcome."""
    provenance: dict[str, Any] = (
        {
            "passage_id": passage.id,
            "document_id": passage.document_id,
            "document_title": passage.document_title,
            "heading_path": list(passage.heading_path),
            "passage_text": passage.text,
        }
        if passage is not None
        else {
            "passage_id": citation.passage_id,
            "document_id": None,
            "document_title": None,
            "heading_path": [],
            "passage_text": None,
        }
    )

    if not citation.quote.strip():
        return CitationResolution(**provenance, failure_reason="empty_quote")
    if passage is None:
        return CitationResolution(**provenance, failure_reason="passage_not_found")

    offsets = resolve_citation(citation.quote, passage.text)
    if offsets is None:
        return CitationResolution(**provenance, failure_reason="offset_not_found")

    start, end = offsets
    return CitationResolution(**provenance, start=start, end=end)


__all__ = ["resolve_answer", "resolve_citation"]
