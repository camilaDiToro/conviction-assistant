"""Per-request agent-loop overrides.

A small dataclass that carries optional overrides for the knobs the
agent loop and rewrite stage read from settings. ``None`` on any field
means "use the server default" (``settings.X``).

The override surface is intentionally narrow: only knobs that are safe
for the user to set per-request live here. Things like the BM25
retriever or the resolver are not exposed.
"""

from dataclasses import dataclass
from typing import Literal

ReasoningEffort = Literal["none", "minimal", "low", "medium", "high", "xhigh"]


@dataclass(frozen=True, slots=True)
class AgentOverrides:
    reasoning_effort: ReasoningEffort | None = None
    rewrite_reasoning_effort: ReasoningEffort | None = None
    agent_max_tool_calls: int | None = None
    agent_max_output_tokens: int | None = None


__all__ = ["AgentOverrides", "ReasoningEffort"]
