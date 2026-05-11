"""Fixture-driven stub provider for CI — never burn provider tokens.

`StubLLM` returns a queue of canned `LLMResponse`s and records every
`generate` call on `self.calls` so tests can assert on the messages,
tools, and schema sent. `load_stub_responses(yaml_path)` builds the
same list from YAML for longer agent-loop flows.
"""

from collections import deque
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast, get_args

import yaml

from app.providers.base import (
    FinishReason,
    LLMResponse,
    Message,
    ProviderError,
    ReasoningEffort,
    StructuredOutputSchema,
    TokenUsage,
    ToolCall,
    ToolDefinition,
)

_FINISH_REASONS: frozenset[str] = frozenset(get_args(FinishReason))


@dataclass(slots=True)
class StubCall:
    """One captured ``generate`` invocation, for test assertions."""

    messages: list[Message]
    tools: list[ToolDefinition] = field(default_factory=list)
    schema: StructuredOutputSchema | None = None
    reasoning_effort: ReasoningEffort | None = None
    max_output_tokens: int | None = None


class StubLLM:
    """`LLMProvider` returning a queue of canned responses; raises
    `ProviderError` if exhausted (loud failure beats silent re-use)."""

    def __init__(self, responses: Sequence[LLMResponse]) -> None:
        self._responses: deque[LLMResponse] = deque(responses)
        self.calls: list[StubCall] = []

    async def generate(
        self,
        messages: list[Message],
        *,
        tools: list[ToolDefinition] | None = None,
        schema: StructuredOutputSchema | None = None,
        reasoning_effort: ReasoningEffort | None = None,
        max_output_tokens: int | None = None,
    ) -> LLMResponse:
        self.calls.append(
            StubCall(
                messages=list(messages),
                tools=list(tools or []),
                schema=schema,
                reasoning_effort=reasoning_effort,
                max_output_tokens=max_output_tokens,
            )
        )
        if not self._responses:
            raise ProviderError(
                "StubLLM exhausted: test issued more generate() calls than canned responses"
            )
        return self._responses.popleft()


# ---- YAML loader ----------------------------------------------------


def load_stub_responses(path: Path) -> list[LLMResponse]:
    """Load `LLMResponse`s from a YAML list. See
    `tests/fixtures/stub_responses_example.yaml` for the schema."""
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ProviderError(f"stub fixture {path} must be a YAML list")
    responses: list[LLMResponse] = []
    for index, entry in enumerate(raw):
        if not isinstance(entry, dict):
            raise ProviderError(f"stub fixture {path} entry {index} must be a mapping")
        responses.append(_parse_response_entry(entry, index, path))
    return responses


def _parse_response_entry(entry: dict[str, Any], index: int, path: Path) -> LLMResponse:
    usage_raw = entry.get("usage")
    if not isinstance(usage_raw, dict):
        raise ProviderError(f"stub fixture {path} entry {index}: missing 'usage' mapping")
    usage = TokenUsage(**usage_raw)

    tool_calls: list[ToolCall] = []
    for tc_index, tc_raw in enumerate(entry.get("tool_calls", []) or []):
        if not isinstance(tc_raw, dict):
            raise ProviderError(
                f"stub fixture {path} entry {index} tool_call {tc_index}: must be a mapping"
            )
        tool_calls.append(
            ToolCall(
                id=tc_raw.get("id", f"call_{index}_{tc_index}"),
                name=tc_raw["name"],
                arguments=tc_raw.get("arguments", {}),
            )
        )

    raw_finish = entry.get("finish_reason")
    if raw_finish is None:
        raw_finish = "tool_calls" if tool_calls else "stop"
    if raw_finish not in _FINISH_REASONS:
        raise ProviderError(
            f"stub fixture {path} entry {index}: unknown finish_reason {raw_finish!r}"
        )

    return LLMResponse(
        content=entry.get("content"),
        tool_calls=tool_calls,
        parsed=entry.get("parsed"),
        usage=usage,
        finish_reason=cast(FinishReason, raw_finish),
    )
