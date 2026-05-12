"""Offset resolver: substring search over Citation + Passage.

Returns (start, end) into the **original** passage text. To absorb the
common cosmetic diffs that came up in evals (smart quotes, NBSP,
en/em dash, compatibility forms), both the quote and passage are
length-preservingly normalized before the search — every fold maps
one source char to one target char so offsets stay aligned with the
original passage. Quotes that still don't anchor after normalization
surface in the citations block without a highlight.

The agent loop's adapter (app.agent.audit.resolve_output) loads
passages and hands them in.
"""

import unicodedata
from typing import TYPE_CHECKING, Any

from app.agent.resolver.base import CitationResolution, OffsetResolution
from app.schemas.passage import Passage

if TYPE_CHECKING:
    from app.agent.schemas import AnswerOutput, Citation


# 1:1 char substitutions. Length-preserving so the normalized index ==
# the original index — no offset map needed.
_FOLD_TABLE: dict[int, str] = {
    # double quotes
    0x201C: '"',  # LEFT DOUBLE QUOTATION MARK
    0x201D: '"',  # RIGHT DOUBLE QUOTATION MARK
    0x201E: '"',  # DOUBLE LOW-9 QUOTATION MARK
    0x201F: '"',  # DOUBLE HIGH-REVERSED-9
    0x00AB: '"',  # « LEFT-POINTING DOUBLE ANGLE
    0x00BB: '"',  # » RIGHT-POINTING DOUBLE ANGLE
    # single quotes / apostrophes
    0x2018: "'",  # LEFT SINGLE QUOTATION MARK
    0x2019: "'",  # RIGHT SINGLE QUOTATION MARK (also typographic apostrophe)
    0x201A: "'",  # SINGLE LOW-9 QUOTATION MARK
    0x201B: "'",  # SINGLE HIGH-REVERSED-9
    # dashes
    0x2013: "-",  # EN DASH
    0x2014: "-",  # EM DASH
    0x2212: "-",  # MINUS SIGN
    # spaces / non-breaking
    0x00A0: " ",  # NO-BREAK SPACE
    0x202F: " ",  # NARROW NO-BREAK SPACE
    0x2009: " ",  # THIN SPACE
}


def _normalize_char(ch: str) -> str:
    """Return a length-1 fold of `ch` for substring matching. If the
    char is in the explicit table, fold it. Otherwise apply NFKC and
    keep the result ONLY when it is still one code point — multi-char
    decompositions (ligatures, fractions) would break offset alignment
    so we leave them as-is and accept the anchor miss."""
    folded = _FOLD_TABLE.get(ord(ch))
    if folded is not None:
        return folded
    nfkc = unicodedata.normalize("NFKC", ch)
    return nfkc if len(nfkc) == 1 else ch


def _normalize(text: str) -> str:
    return "".join(_normalize_char(c) for c in text)


def resolve_citation(quote: str, passage_text: str) -> tuple[int, int] | None:
    """First (start, end) of `quote` in `passage_text`, or None if empty
    or not a substring after normalization. Offsets index the original
    passage_text — the half-open slice passage_text[start:end] may
    differ from `quote` only in cosmetic chars (smart quotes, dashes,
    NBSP) that the resolver folded for matching."""
    if not quote:
        return None
    idx = passage_text.find(quote)
    if idx != -1:
        return idx, idx + len(quote)
    norm_quote = _normalize(quote)
    norm_text = _normalize(passage_text)
    idx = norm_text.find(norm_quote)
    if idx == -1:
        return None
    return idx, idx + len(norm_quote)


def resolve_answer(
    answer: "AnswerOutput",
    passages: dict[str, Passage],
) -> OffsetResolution:
    """Resolve every citation against the passage map. Order preserved.

    Outcomes: empty quote → 'empty_quote'; passage_id missing →
    'passage_not_found'; non-substring quote → 'offset_not_found';
    match → anchored with (start, end). Caller populates the map
    (see app.agent.audit.resolve_output).
    """
    return OffsetResolution(
        entries=[_resolve_one(c, passages.get(c.passage_id)) for c in answer.citations]
    )


def _resolve_one(citation: "Citation", passage: Passage | None) -> CitationResolution:
    """Resolve one citation. Provenance comes from `passage` if present,
    else nullified — independent of the outcome."""
    provenance: dict[str, Any] = (
        {
            "passage_id": passage.id,
            "document_id": passage.document_id,
            "document_title": passage.document_title,
            "heading_path": list(passage.heading_path),
            "passage_text": passage.text,
        }
        if passage is not None
        else {
            "passage_id": citation.passage_id,
            "document_id": None,
            "document_title": None,
            "heading_path": [],
            "passage_text": None,
        }
    )

    if not citation.quote.strip():
        return CitationResolution(**provenance, failure_reason="empty_quote")
    if passage is None:
        return CitationResolution(**provenance, failure_reason="passage_not_found")

    offsets = resolve_citation(citation.quote, passage.text)
    if offsets is None:
        return CitationResolution(**provenance, failure_reason="offset_not_found")

    start, end = offsets
    return CitationResolution(**provenance, start=start, end=end)


__all__ = ["resolve_answer", "resolve_citation"]
