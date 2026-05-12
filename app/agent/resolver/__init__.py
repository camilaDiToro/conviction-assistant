"""Citation resolver — turns each model quote into (start, end) offsets
in the cited passage. Pure, no I/O.

The model copies a verbatim quote; the resolver locates it via str.find.
The literal quote is discarded — only offsets reach the wire response.
Non-anchoring citations still surface, but without a highlight.
"""

from app.agent.resolver.base import (
    CitationResolution,
    OffsetResolution,
    UnresolutionReason,
)
from app.agent.resolver.substring import resolve_answer, resolve_citation

__all__ = [
    "CitationResolution",
    "OffsetResolution",
    "UnresolutionReason",
    "resolve_answer",
    "resolve_citation",
]
