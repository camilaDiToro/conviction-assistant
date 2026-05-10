"""Deterministic substring verifier for citations.

The verifier is the architectural commitment of this project: every
``Citation`` produced by the agent must contain a ``quote`` that is a
verbatim substring of the cited passage's ``text`` (after the pinned
normalization in ``app.verifier.normalize``). No LLM-as-judge, no
fuzzy match — the verifier either says the substring is there or it
isn't.

This module is **pure**: it knows nothing about repositories,
sessions, the LLM, or settings. The agent loop (or any caller) is
responsible for fetching passages by id and handing them in.
"""

from datetime import date
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict

from app.schemas.passage import Passage
from app.verifier.normalize import normalize

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


def verify_citation(quote: str, passage_text: str) -> bool:
    """Return True iff ``quote`` is a substring of ``passage_text``
    after normalization. Empty quote is always False.
    """
    nq = normalize(quote)
    if not nq:
        return False
    return nq in normalize(passage_text)


def verify_answer(
    answer: "AnswerOutput",
    passages: dict[str, Passage],
) -> VerificationResult:
    """Verify every citation in ``answer`` against the passage map.

    ``passages`` maps ``passage_id`` → ``Passage``. A citation whose
    ``passage_id`` is not in the map fails with reason
    ``"passage_not_found"``. The caller (typically the agent loop's
    ``_verify_output`` helper) is responsible for populating the map
    via the passage repository.
    """
    verified: list[VerifiedCitation] = []
    failures: list[CitationFailure] = []

    for index, citation in enumerate(answer.citations):
        if not citation.quote.strip():
            failures.append(
                CitationFailure(
                    index=index,
                    passage_id=citation.passage_id,
                    quote=citation.quote,
                    reason="empty_quote",
                )
            )
            continue

        passage = passages.get(citation.passage_id)
        if passage is None:
            failures.append(
                CitationFailure(
                    index=index,
                    passage_id=citation.passage_id,
                    quote=citation.quote,
                    reason="passage_not_found",
                )
            )
            continue

        if not verify_citation(citation.quote, passage.text):
            failures.append(
                CitationFailure(
                    index=index,
                    passage_id=citation.passage_id,
                    quote=citation.quote,
                    reason="substring_not_found",
                )
            )
            continue

        verified.append(
            VerifiedCitation(
                passage_id=passage.id,
                document_id=passage.document_id,
                document_title=passage.document_title,
                heading_path=passage.heading_path,
                document_updated=passage.document_updated,
                quote=citation.quote,
            )
        )

    return VerificationResult(verified=verified, failures=failures)


__all__ = [
    "CitationFailure",
    "FailureReason",
    "VerificationResult",
    "VerifiedCitation",
    "verify_answer",
    "verify_citation",
]
