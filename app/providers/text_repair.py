"""Repair model-output text artifacts that are wrong-on-the-wire.

Right now this module fixes one specific bug: some models (notably
gpt-5-mini circa 2026-05) emit JSON unicode escapes with 6 hex digits
(``\\u0000e9``) instead of the spec-mandated 4 (``\\u00e9``). JSON
parsers correctly read ``\\u0000e9`` as U+0000 + literal "e9"; what was
actually intended was U+00E9 ("é"). The user-visible symptom is
accented Latin-1 characters showing up as their hex code (Crédito
becomes "Cr\\x00e9dito" → rendered as "Cre9dito").

The repair is conservative — it only matches the very specific
``NUL + 2 hex digits`` sequence, which essentially never appears in
natural text — so it's safe to apply in both the live OpenAI adapter
path (parse time) and at audit-log read time for text persisted
before this fix landed.
"""

from __future__ import annotations

import re
from typing import Any

_BROKEN_LATIN1_ESCAPE = re.compile(r"\x00([0-9a-fA-F]{2})")


def repair_broken_unicode_escapes(s: str) -> str:
    """Replace ``NUL + 2 hex digits`` with the corresponding Latin-1
    character. Idempotent on clean input.
    """
    if not s:
        return s
    return _BROKEN_LATIN1_ESCAPE.sub(lambda m: chr(int(m.group(1), 16)), s)


def repair_strings_in(value: Any) -> Any:
    """Walk ``value`` recursively, applying the repair to every string.
    Returns a structurally-identical container with the same types.
    """
    if isinstance(value, str):
        return repair_broken_unicode_escapes(value)
    if isinstance(value, dict):
        return {k: repair_strings_in(v) for k, v in value.items()}
    if isinstance(value, list):
        return [repair_strings_in(v) for v in value]
    return value


__all__ = ["repair_broken_unicode_escapes", "repair_strings_in"]
