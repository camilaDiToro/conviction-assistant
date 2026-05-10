"""Deterministic citation verifier (B8) — agent-internal policy module.

See ``app.agent.verifier.normalize`` for the pinned normalization policy
and ``app.agent.verifier.substring`` for the substring check + result shape.
"""

from app.agent.verifier.normalize import normalize
from app.agent.verifier.substring import (
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
