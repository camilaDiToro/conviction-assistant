"""Result types for the offset resolver.

One ordered list of :class:`CitationResolution` entries, one per
``Citation`` the model emitted, in the model's original order. The
literal quote is **not** kept here — it is consumed during resolution
and discarded; only ``(start, end)`` offsets survive (or ``None`` /
``failure_reason`` when the quote did not anchor).

Single-type-with-nullable-fields rather than a discriminated union
because the wire layer renders the cases uniformly: every citation
shows the passage in the popup; the highlight is conditional on
``start`` / ``end`` being non-null.

Invariants enforced by :func:`resolve_answer`:

- ``start`` and ``end`` are both ``int`` and ``failure_reason is None``
  when the quote anchored.
- ``start`` and ``end`` are both ``None`` and ``failure_reason`` carries
  the reason when it did not.
- ``passage_text`` is ``None`` only for ``failure_reason='passage_not_found'``.
"""

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict

UnresolutionReason = Literal["empty_quote", "passage_not_found", "offset_not_found"]


class CitationResolution(BaseModel):
    """One citation after offset resolution.

    Carries the passage provenance the wire response needs (so the
    frontend popup needs no extra ``read_passage`` round-trip) plus the
    ``(start, end)`` offsets when the model's quote anchored to a
    literal substring of the passage. When ``failure_reason`` is set the
    citation still surfaces in the response — the popup shows the
    passage without a highlight.
    """

    model_config = ConfigDict(extra="forbid")

    passage_id: str
    document_id: str | None
    document_title: str | None
    heading_path: list[str]
    document_updated: date | None
    passage_text: str | None
    start: int | None = None
    end: int | None = None
    failure_reason: UnresolutionReason | None = None


class OffsetResolution(BaseModel):
    """Outcome of resolving one ``AnswerOutput``'s citations.

    ``entries`` preserves the model's original ``answer.citations``
    order so inline ``[N]`` markers stay aligned. The wire layer maps
    one ``CitationResolution`` to one ``ChatCitation``; the debug drawer
    splits them by ``failure_reason`` for the operator.
    """

    model_config = ConfigDict(extra="forbid")

    entries: list[CitationResolution]

    @property
    def all_anchored(self) -> bool:
        return all(e.failure_reason is None for e in self.entries)


__all__ = [
    "CitationResolution",
    "OffsetResolution",
    "UnresolutionReason",
]
