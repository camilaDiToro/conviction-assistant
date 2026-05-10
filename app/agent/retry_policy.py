"""Verifier-failure handling: compose feedback, strip failed citations, refuse safely.

The retry behavior pinned by ROADMAP B8 is a sequence of three named steps:

1. **First failure** → :func:`compose_feedback` produces a user-role
   message naming each failed citation, echoing the model's quote and
   the passage's actual prefix so the model can retry verbatim.
2. **Second failure** → :func:`strip_failed_citations` drops the
   offending citation rows from the answer.
3. **Zero grounded citations remain** → :func:`localized_refusal` builds
   a safe-refusal :class:`AnswerOutput` in the user's language.

This module is the seam for the documented "re-search-then-retry" level-up:
if/when that lands, this file grows or splits and a Protocol earns its
keep. Today it is plain functions — the policy is one specification.
"""

from app.agent.language import detect_language
from app.agent.schemas import AnswerOutput
from app.repositories import passages as passages_repo
from app.tools import ToolContext
from app.verifier import VerificationResult


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


__all__ = ["compose_feedback", "localized_refusal", "strip_failed_citations"]
