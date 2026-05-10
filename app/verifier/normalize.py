"""Normalization policy for the citation verifier.

Pinned policy (see ROADMAP B8 — changes go through code review):

1. **NFC** unicode normalization on both the quote and the passage text.
2. **Strip** soft-hyphens (U+00AD) and zero-width characters
   (U+200B, U+200C, U+200D, U+FEFF).
3. **Fold smart quotes** to ASCII:
   ``" " " " ‹ ›`` → ``"`` and ``' ' ' '`` → ``'``.
4. **Normalize dashes**: em-dash (U+2014) and en-dash (U+2013)
   → ASCII hyphen-minus (U+002D).
5. **Collapse runs of internal whitespace** (including NBSP U+00A0
   and U+202F narrow no-break space) to a single ASCII space.
6. **Strip leading and trailing whitespace.**
7. **Diacritics are preserved.** PT/ES users need them to round-trip;
   stripping them would make the verifier accept paraphrases.

Why this set: the publishing toolchain that produced the markdown
corpus introduces these classes of cosmetic difference (NBSPs from
copy-paste, smart quotes from auto-correct, soft hyphens from PDF
ingest) without changing meaning. Anything beyond cosmetic
differences must fail verification — including any change of letter,
number, or diacritic.
"""

import re
import unicodedata

_ZERO_WIDTH = "­​‌‍﻿"
_ZW_TABLE = str.maketrans({ch: None for ch in _ZERO_WIDTH})

_QUOTE_TABLE = str.maketrans(
    {
        "“": '"',
        "”": '"',
        "„": '"',
        "‟": '"',
        "«": '"',
        "»": '"',
        "‘": "'",
        "’": "'",
        "‚": "'",
        "‛": "'",
        "‹": "'",
        "›": "'",
    }
)

_DASH_TABLE = str.maketrans({"–": "-", "—": "-"})

# Whitespace runs include any unicode whitespace plus NBSP variants;
# Python's \s already matches   and   under `re.UNICODE` (default).
_WS_RUN = re.compile(r"\s+")


def normalize(text: str) -> str:
    """Apply the pinned normalization policy. See module docstring."""
    if not text:
        return ""
    text = unicodedata.normalize("NFC", text)
    text = text.translate(_ZW_TABLE)
    text = text.translate(_QUOTE_TABLE)
    text = text.translate(_DASH_TABLE)
    text = _WS_RUN.sub(" ", text)
    return text.strip()


__all__ = ["normalize"]
