"""Provider-agnostic protocols and request/response types.

The contract above provider adapters is identical: every adapter
(``openai.py``, ``stub.py``, the future ``anthropic.py``) accepts the same
``Message`` / ``ToolDefinition`` / ``StructuredOutputSchema`` inputs and
returns the same ``LLMResponse`` / ``EmbeddingResponse`` shape.

Cost in USD is *not* a field on ``TokenUsage`` — adapters return raw
token counts and ``app/services/cost.py`` derives USD from
``app/providers/_model_prices.json`` at audit-log read time. This keeps
prices out of the hot path and makes price corrections retroactive.
"""

from typing import Any, Literal, Protocol

from pydantic import BaseModel, Field


class ProviderError(Exception):
    """Raised by a provider adapter when the upstream call fails or the
    response cannot be mapped to the provider-agnostic contract.
    """


Role = Literal["system", "user", "assistant", "tool"]


class ToolDefinition(BaseModel):
    """One tool the model is allowed to call."""

    name: str
    description: str
    parameters: dict[str, Any]


class StructuredOutputSchema(BaseModel):
    """JSON-schema contract for the model's final answer."""

    name: str
    json_schema: dict[str, Any]


class ToolCall(BaseModel):
    """A tool call requested by the model."""

    id: str
    name: str
    arguments: dict[str, Any]


class Message(BaseModel):
    """One turn in the conversation, in provider-agnostic form.

    Field semantics by role:

    - ``system`` / ``user``: ``content`` is the text. Other fields ignored.
    - ``assistant``: either ``content`` is set (text answer) or
      ``tool_calls`` is non-empty (the model wants to call tools), or
      both. Adapters translate accordingly.
    - ``tool``: ``content`` is the tool result text and ``tool_call_id``
      identifies which assistant tool call this is responding to.
    """

    role: Role
    content: str | None = None
    tool_calls: list[ToolCall] = Field(default_factory=list)
    tool_call_id: str | None = None


class TokenUsage(BaseModel):
    """Token counts for one provider call.

    USD pricing lives in ``app/services/cost.py`` — adapters never compute
    cost. ``model`` must match a key in ``app/providers/_model_prices.json``
    so the cost layer can look up the input, output, and cached-token rates.
    """

    model: str
    prompt_tokens: int
    completion_tokens: int
    cached_tokens: int = 0
    reasoning_tokens: int = 0
    reasoning_effort: str | None = None


FinishReason = Literal["stop", "tool_calls", "length", "content_filter", "other"]


class LLMResponse(BaseModel):
    """One assistant turn produced by an ``LLMProvider``.

    Exactly one of ``content`` or ``tool_calls`` will be populated for a
    well-behaved response. ``parsed`` is set only when the call provided
    a ``StructuredOutputSchema`` and the adapter successfully decoded
    the model's output against it.
    """

    content: str | None = None
    tool_calls: list[ToolCall] = Field(default_factory=list)
    parsed: dict[str, Any] | None = None
    usage: TokenUsage
    finish_reason: FinishReason = "stop"


class EmbeddingResponse(BaseModel):
    """One batch of embedding vectors + token usage."""

    vectors: list[list[float]]
    usage: TokenUsage


ReasoningEffort = Literal["none", "minimal", "low", "medium", "high", "xhigh"]
Verbosity = Literal["low", "medium", "high"]


class LLMProvider(Protocol):
    """The single contract the orchestrator and tests program against.

    Implementations: ``OpenAILLM`` (``openai.py``), ``StubLLM``
    (``stub.py``), and the future ``AnthropicLLM``.
    """

    async def generate(
        self,
        messages: list[Message],
        *,
        tools: list[ToolDefinition] | None = None,
        schema: StructuredOutputSchema | None = None,
        temperature: float | None = None,
        reasoning_effort: ReasoningEffort | None = None,
        verbosity: Verbosity | None = None,
        max_output_tokens: int | None = None,
    ) -> LLMResponse: ...


class EmbeddingProvider(Protocol):
    """Embedding contract."""

    async def embed(self, texts: list[str]) -> EmbeddingResponse: ...
