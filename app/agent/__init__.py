"""Agent orchestrator: bounded tool-using loop + structured output.

Public surface:

- :func:`run` — orchestrates the rewrite stage (skipped on empty history)
  and the agent loop. Returns an :class:`AgentResult`.
- :class:`AgentResult` and the structured output Pydantic models that
  the rest of the project (the HTTP wrapper) consumes.

Per the architecture (``docs/ARCHITECTURES.md`` § Conversation memory),
prior assistant text is **never** injected into the agent loop's
tool-call context. The rewrite stage is the quarantine between
conversation memory and grounded retrieval.
"""

from app.agent.loop import run
from app.agent.schemas import (
    AgentOutput,
    AgentResult,
    AnswerOutput,
    Citation,
    ClarifyingQuestionOutput,
    ConversationTurn,
    StepRecord,
)

__all__ = [
    "AgentOutput",
    "AgentResult",
    "AnswerOutput",
    "Citation",
    "ClarifyingQuestionOutput",
    "ConversationTurn",
    "StepRecord",
    "run",
]
