"""The offset resolver itself.

Pure functions over ``Citation`` and ``Passage``: no DB, no session, no
LLM. The agent loop's adapter (:func:`app.agent.audit.resolve_output`)
loads passages and hands them in.

``resolve_citation`` is a literal substring search — it does not apply
the smart-quote / NBSP / dash normalization the old verifier used.
Rationale: the model copies its quote from the result of ``read_passage``,
which returns the DB-stored passage text verbatim, so cosmetic
differences essentially never appear. When they do, the citation still
surfaces with offsets ``None`` and the popup shows the passage with no
highlight — better than the cost of a normalized index map.
"""

from typing import TYPE_CHECKING

from app.agent.resolver.base import CitationResolution, OffsetResolution
from app.schemas.passage import Passage

if TYPE_CHECKING:
    from app.agent.schemas import AnswerOutput


def resolve_citation(quote: str, passage_text: str) -> tuple[int, int] | None:
    """Return ``(start, end)`` offsets of ``quote`` inside ``passage_text``.

    Returns ``None`` if the quote is empty or is not a literal substring.
    Half-open bounds: ``passage_text[start:end] == quote``.
    """
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
    """Resolve every citation in ``answer`` against the passage map.

    ``passages`` maps ``passage_id`` → ``Passage``. A citation whose
    ``passage_id`` is missing falls to ``failure_reason='passage_not_found'``;
    an empty quote falls to ``'empty_quote'``; a non-substring quote
    falls to ``'offset_not_found'``. The caller populates the map (see
    :func:`app.agent.audit.resolve_output`).

    Order is preserved one-to-one with ``answer.citations``.
    """
    entries: list[CitationResolution] = []

    for citation in answer.citations:
        passage = passages.get(citation.passage_id)

        if not citation.quote.strip():
            entries.append(
                CitationResolution(
                    passage_id=citation.passage_id,
                    document_id=passage.document_id if passage else None,
                    document_title=passage.document_title if passage else None,
                    heading_path=list(passage.heading_path) if passage else [],
                    document_updated=passage.document_updated if passage else None,
                    passage_text=passage.text if passage else None,
                    failure_reason="empty_quote",
                )
            )
            continue

        if passage is None:
            entries.append(
                CitationResolution(
                    passage_id=citation.passage_id,
                    document_id=None,
                    document_title=None,
                    heading_path=[],
                    document_updated=None,
                    passage_text=None,
                    failure_reason="passage_not_found",
                )
            )
            continue

        offsets = resolve_citation(citation.quote, passage.text)
        if offsets is None:
            entries.append(
                CitationResolution(
                    passage_id=passage.id,
                    document_id=passage.document_id,
                    document_title=passage.document_title,
                    heading_path=list(passage.heading_path),
                    document_updated=passage.document_updated,
                    passage_text=passage.text,
                    failure_reason="offset_not_found",
                )
            )
            continue

        start, end = offsets
        entries.append(
            CitationResolution(
                passage_id=passage.id,
                document_id=passage.document_id,
                document_title=passage.document_title,
                heading_path=list(passage.heading_path),
                document_updated=passage.document_updated,
                passage_text=passage.text,
                start=start,
                end=end,
            )
        )

    return OffsetResolution(entries=entries)


__all__ = ["resolve_answer", "resolve_citation"]
