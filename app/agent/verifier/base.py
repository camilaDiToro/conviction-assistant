"""Verifier Protocol + result types — the deterministic-grounding contract.

The substring guarantee is the architectural commitment of this project:
every cited quote must be a verbatim substring of the source passage
(after pinned normalization). The Protocol exists so future variants
(fuzzy / semantic / LLM-judge) can register, but they ship as
deliberate code changes — never as a silent ``.env`` flip. See
``docs/ARCHITECTURES.md`` § "The citation verifier".

Result types live here (not in ``substring.py``) so adding a new
implementation doesn't create import cycles.
"""

from datetime import date
from typing import TYPE_CHECKING, Literal, Protocol

from pydantic import BaseModel, ConfigDict

from app.schemas.passage import Passage

if TYPE_CHECKING:
    from app.agent.schemas import AnswerOutput


FailureReason = Literal["substring_not_found", "passage_not_found", "empty_quote"]


class VerifiedCitation(BaseModel):
    """One citation that successfully verified.

    Carries full passage provenance so downstream (B9, frontend) can
    render *which document and which passage was quoted* without an
    extra ``read_passage`` round-trip.
    """

    model_config = ConfigDict(extra="forbid")

    passage_id: str
    document_id: str
    document_title: str
    heading_path: list[str]
    document_updated: date | None
    quote: str


class CitationFailure(BaseModel):
    """One citation that failed verification."""

    model_config = ConfigDict(extra="forbid")

    index: int
    passage_id: str
    quote: str
    reason: FailureReason


class VerificationResult(BaseModel):
    """Outcome of verifying one ``AnswerOutput``.

    ``verified`` contains only the citations that passed, in their
    original ``answer.citations`` order. ``failures`` carries each
    failed citation's index in the original list so callers can strip
    by index.
    """

    model_config = ConfigDict(extra="forbid")

    verified: list[VerifiedCitation]
    failures: list[CitationFailure]

    @property
    def all_passed(self) -> bool:
        return not self.failures


class Verifier(Protocol):
    """The single contract every verifier strategy implements.

    The substring guarantee is the architectural commitment; alternative
    implementations are allowed by this Protocol but must preserve a
    binary ``all_passed`` outcome — no soft confidence scores. See
    ``docs/ARCHITECTURES.md``.
    """

    def verify(
        self,
        answer: "AnswerOutput",
        passages: dict[str, Passage],
    ) -> VerificationResult: ...


__all__ = [
    "CitationFailure",
    "FailureReason",
    "VerificationResult",
    "VerifiedCitation",
    "Verifier",
]
