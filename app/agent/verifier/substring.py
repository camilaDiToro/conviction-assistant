"""Deterministic substring verifier — the architectural commitment.

Every ``Citation`` produced by the agent must contain a ``quote`` that
is a verbatim substring of the cited passage's ``text`` (after the
pinned normalization in :mod:`app.agent.verifier.normalize`). No
LLM-as-judge, no fuzzy match — the verifier either says the substring
is there or it isn't.

This module is **pure**: it knows nothing about repositories, sessions,
the LLM, or settings. The agent loop (or any caller) is responsible for
fetching passages by id and handing them in.

Result types (``VerificationResult``, ``VerifiedCitation``,
``CitationFailure``, ``FailureReason``) live in :mod:`app.agent.verifier.base`
so they're owned by the contract, not this implementation.
"""

from typing import TYPE_CHECKING

from app.agent.verifier.base import (
    CitationFailure,
    VerificationResult,
    VerifiedCitation,
    Verifier,
)
from app.agent.verifier.normalize import normalize
from app.agent.verifier.registry import register
from app.schemas.passage import Passage

if TYPE_CHECKING:
    from app.agent.schemas import AnswerOutput


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
    ``verify_output`` adapter in :mod:`app.agent.audit`) is responsible
    for populating the map via the passage repository.
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


class SubstringVerifier:
    """The :class:`Verifier` adapter wrapping :func:`verify_answer`.

    Stateless. Held on ``app.state.verifier`` after lifespan resolves
    ``settings.verifier_strategy``. The free :func:`verify_answer` and
    :func:`verify_citation` functions remain as the canonical
    implementation; this class is the Protocol-conforming surface.
    """

    def verify(
        self,
        answer: "AnswerOutput",
        passages: dict[str, Passage],
    ) -> VerificationResult:
        return verify_answer(answer, passages)


@register("substring")
def _substring_factory() -> Verifier:
    return SubstringVerifier()


__all__ = ["SubstringVerifier", "verify_answer", "verify_citation"]
