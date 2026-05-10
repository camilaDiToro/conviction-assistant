"""Citation resolver — pure substring → offsets, no I/O.

The architectural commitment of this project: every citation the agent
produces is anchored to a specific ``(start, end)`` region of the cited
passage. The model copies a verbatim quote (because LLMs copy substrings
reliably but cannot count characters); the resolver finds that quote in
the passage text and turns it into offsets. The literal quote is
consumed here and never reaches storage or the HTTP response.

Provider-agnostic, deterministic, and trivial to test: ``resolve_citation``
is a literal ``str.find`` wrapped in result types. When the substring
isn't found, the citation still surfaces but with offsets ``None`` —
the popup shows the passage without a highlight (chosen fallback).
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
