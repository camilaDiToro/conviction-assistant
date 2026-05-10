"""Deterministic citation verifier (B8).

See ``app.verifier.normalize`` for the pinned normalization policy
and ``app.verifier.substring`` for the substring check + result shape.
"""

from app.verifier.normalize import normalize
from app.verifier.substring import (
    CitationFailure,
    FailureReason,
    VerificationResult,
    VerifiedCitation,
    verify_answer,
    verify_citation,
)

__all__ = [
    "CitationFailure",
    "FailureReason",
    "VerificationResult",
    "VerifiedCitation",
    "normalize",
    "verify_answer",
    "verify_citation",
]
