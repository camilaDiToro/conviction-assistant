"""Result types for the resolver.

One CitationResolution per citation, in the model's original order.
The literal quote is consumed during resolution and discarded; only
(start, end) survive — or None + failure_reason when the quote did
not anchor.

Invariants from resolve_answer:
- anchored: start/end are ints, failure_reason is None
- failed: start/end are None, failure_reason is set
- provenance fields are populated iff the passage_id was in the
  resolver's map — independent of failure_reason
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict

UnresolutionReason = Literal["empty_quote", "passage_not_found", "offset_not_found"]


class CitationResolution(BaseModel):
    """One citation after resolution: provenance + (start, end), or
    provenance + failure_reason when the quote did not anchor.

    Provenance lets the popup render the passage without an extra
    read_passage round-trip; failed citations show the passage with
    no highlight.
    """

    model_config = ConfigDict(extra="forbid")

    passage_id: str
    document_id: str | None
    document_title: str | None
    heading_path: list[str]
    passage_text: str | None
    start: int | None = None
    end: int | None = None
    failure_reason: UnresolutionReason | None = None


class OffsetResolution(BaseModel):
    """Resolved citations in the model's original order — keeps inline
    [N] markers aligned with the answer text."""

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
