"""LLM-as-judge layer for the eval suite.

Runs **manually from Claude Code**, not from the runtime — the judge
prompt + schema live here so the user can apply them to the trace
JSONL the deterministic runner already emits. The combined report
under :mod:`evals.judge.aggregate` merges the judge JSONL with the
deterministic CSV.

See ``evals/RAGAS_USAGE.md`` for why the judge sits outside the
Ragas runtime.
"""

from evals.judge.schema import (
    AnswerRelevancyScore,
    CitationAttributionScore,
    CompletenessScore,
    FaithfulnessScore,
    JudgeResult,
    RuleAPurityScore,
)

__all__ = [
    "AnswerRelevancyScore",
    "CitationAttributionScore",
    "CompletenessScore",
    "FaithfulnessScore",
    "JudgeResult",
    "RuleAPurityScore",
]
