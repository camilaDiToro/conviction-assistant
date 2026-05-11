"""Collapse duplicate citations by ``passage_id`` and remap ``[N]`` markers.

`dedupe_citations` keeps the **first** citation per ``passage_id``
and drops the rest. Inline ``[N]`` markers in ``output.answer``
(1-indexed) are rewritten through an ``old_index → new_index`` remap.
"""

import re

from app.agent.schemas import AnswerOutput, Citation

_MARKER_RE = re.compile(r"\[(\d+)\]")


def dedupe_citations(output: AnswerOutput) -> AnswerOutput:
    """Return a copy of ``output`` with citations deduplicated by ``passage_id``."""
    seen: dict[str, int] = {}
    deduped: list[Citation] = []
    remap: dict[int, int] = {}
    for old_idx, c in enumerate(output.citations):
        if c.passage_id in seen:
            remap[old_idx] = seen[c.passage_id]
            continue
        new_idx = len(deduped)
        seen[c.passage_id] = new_idx
        deduped.append(c)
        remap[old_idx] = new_idx

    if len(deduped) == len(output.citations):
        return output

    def _rewrite(match: re.Match[str]) -> str:
        n = int(match.group(1))
        if n < 1 or n > len(output.citations):
            return match.group(0)
        return f"[{remap[n - 1] + 1}]"

    new_answer = _MARKER_RE.sub(_rewrite, output.answer)
    return output.model_copy(update={"answer": new_answer, "citations": deduped})


__all__ = ["dedupe_citations"]
