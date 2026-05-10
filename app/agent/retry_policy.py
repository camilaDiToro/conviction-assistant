"""Verifier-failure handling: compose feedback, strip failed citations, refuse safely.

The retry behavior pinned by ROADMAP B8 is a sequence of three named steps:

1. **First failure** → :func:`compose_feedback` produces a user-role
   message naming each failed citation, echoing the model's quote and
   the passage's actual prefix so the model can retry verbatim.
2. **Second failure** → :func:`strip_failed_citations` drops the
   offending citation rows from the answer.
3. **Zero grounded citations remain** → :func:`localized_refusal` builds
   a safe-refusal :class:`AnswerOutput` in the user's language.

A fourth helper, :func:`dedupe_citations`, runs **after** verification on
the success path: it collapses duplicate citations by ``passage_id`` and
remaps inline ``[N]`` markers in ``answer`` so the user sees one card
per passage instead of one per claim.

This module is the seam for the documented "re-search-then-retry" level-up:
if/when that lands, this file grows or splits and a Protocol earns its
keep. Today it is plain functions — the policy is one specification.
"""

import re

from app.agent.language import detect_language
from app.agent.schemas import AnswerOutput, Citation
from app.agent.tools import ToolContext
from app.agent.verifier import VerificationResult
from app.repositories import passages as passages_repo

_MARKER_RE = re.compile(r"\[(\d+)\]")


async def compose_feedback(result: VerificationResult, *, ctx: ToolContext) -> str:
    """User-role retry prompt sent after the first verification failure.

    For each failed citation, name the passage_id, echo the model's
    quote, the failure reason, and (when the passage exists) the
    first ~200 chars of the passage's actual text.
    """
    lines = [
        "The deterministic citation verifier rejected your previous answer. "
        "The following citation(s) failed verification:",
    ]
    for failure in result.failures:
        lines.append("")
        lines.append(f"- index {failure.index}, passage_id={failure.passage_id!r}")
        lines.append(f"  reason: {failure.reason}")
        lines.append(f"  your quote: {failure.quote!r}")
        if failure.reason == "substring_not_found":
            passage = await passages_repo.get(ctx.session, failure.passage_id)
            if passage is not None:
                preview = passage.text[:200].replace("\n", " ")
                lines.append(f"  passage starts with: {preview!r}")
    lines.append("")
    lines.append(
        "Retry: emit the same answer with verbatim quotes from the cited "
        "passages. If you cannot find a verbatim substring that supports a "
        "claim, remove the claim. Do not paraphrase inside a quote."
    )
    return "\n".join(lines)


def strip_failed_citations(output: AnswerOutput, result: VerificationResult) -> AnswerOutput:
    """Return a copy of ``output`` with the failed citations dropped."""
    failed = {f.index for f in result.failures}
    surviving = [c for i, c in enumerate(output.citations) if i not in failed]
    return output.model_copy(update={"citations": surviving})


_REFUSAL_TEXTS = {
    "pt": (
        "Não consegui localizar uma citação verbatim nas convicções da Decade "
        "para fundamentar uma resposta a esta pergunta. Reformule a pergunta "
        "ou consulte um analista."
    ),
    "es": (
        "No pude localizar una cita literal en las convicciones de Decade que "
        "respalde una respuesta a esta pregunta. Por favor, reformule la "
        "pregunta o consulte a un analista."
    ),
    "en": (
        "I could not locate a verbatim quote in Decade's convictions to ground "
        "an answer to this question. Please rephrase or consult an analyst."
    ),
}


def localized_refusal(question: str) -> AnswerOutput:
    """Safe-refusal :class:`AnswerOutput` in the user's language (PT/ES/EN)."""
    return AnswerOutput(
        answer=_REFUSAL_TEXTS[detect_language(question)],
        citations=[],
        general_knowledge_used=False,
        general_knowledge_section=None,
        out_of_scope=False,
    )


def dedupe_citations(output: AnswerOutput) -> AnswerOutput:
    """Collapse citations by ``passage_id`` and remap ``[N]`` markers in ``answer``.

    The agent often emits one Citation per *claim*, so a passage that
    backs five claims appears as five entries (often with five different
    verbatim substrings). The bottom Citations block then renders five
    cards with the same passage header — visually noisy.

    This helper keeps the **first** citation per ``passage_id`` and drops
    the rest. Inline ``[N]`` markers in ``output.answer`` (1-indexed) are
    rewritten through an ``old_index → new_index`` remap, so claims that
    pointed to dropped duplicates collapse onto the canonical index.

    Markers whose number is out of range (``N == 0`` or ``N > len(citations)``)
    are left untouched.
    """
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


__all__ = [
    "compose_feedback",
    "dedupe_citations",
    "localized_refusal",
    "strip_failed_citations",
]
