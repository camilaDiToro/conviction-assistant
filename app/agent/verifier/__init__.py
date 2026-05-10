"""Deterministic citation verifier — agent-internal Protocol + registry.

The substring guarantee is the architectural commitment of this project.
The Protocol exists so future variants (fuzzy / semantic / LLM-judge)
can register, but they ship as deliberate code changes — never as a
silent ``.env`` flip. See ``docs/ARCHITECTURES.md`` § "The citation
verifier".

Today the only registered strategy is ``substring``.
"""

from app.agent.verifier import substring  # noqa: F401 — registers 'substring'
from app.agent.verifier.base import (
    CitationFailure,
    FailureReason,
    VerificationResult,
    VerifiedCitation,
    Verifier,
)
from app.agent.verifier.normalize import normalize
from app.agent.verifier.registry import VERIFIERS, get_verifier, register
from app.agent.verifier.substring import (
    SubstringVerifier,
    verify_answer,
    verify_citation,
)

__all__ = [
    "VERIFIERS",
    "CitationFailure",
    "FailureReason",
    "SubstringVerifier",
    "VerificationResult",
    "VerifiedCitation",
    "Verifier",
    "get_verifier",
    "normalize",
    "register",
    "verify_answer",
    "verify_citation",
]
