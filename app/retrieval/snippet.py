"""Snippet generation for retrieval results.

Strategy-agnostic: collapse whitespace and truncate at the last word boundary
before `max_chars`. Used by the `search_convictions` tool to build the
short preview shown to the agent — independent of which retriever produced
the hit.
"""

import re

_WHITESPACE_RE = re.compile(r"\s+")


def make_snippet(text: str, max_chars: int = 200) -> str:
    """First ~`max_chars` chars of `text`, cut at the last word boundary."""
    collapsed = _WHITESPACE_RE.sub(" ", text).strip()
    if len(collapsed) <= max_chars:
        return collapsed
    cut = collapsed[: max_chars + 1]
    space = cut.rfind(" ")
    cut = cut[:space] if space > max_chars // 2 else cut[:max_chars]
    return cut.rstrip() + "…"
