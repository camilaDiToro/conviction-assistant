"""OpenAI adapter — direct ``openai`` SDK calls.

Only this module imports the ``openai`` SDK; the rest of the project
talks to providers through ``app.providers.base``.

Tuning kwargs (``temperature``, ``reasoning_effort``, ``verbosity``,
``max_output_tokens``) are forwarded to the API only when non-``None``
— this is what keeps the adapter compatible with reasoning models like
gpt-5, which reject explicit ``temperature``.
"""

import json
from typing import Any, cast

from openai import APIError, AsyncOpenAI

from app.providers.base import (
    EmbeddingResponse,
    FinishReason,
    LLMResponse,
    Message,
    ProviderError,
    ReasoningEffort,
    StructuredOutputSchema,
    TokenUsage,
    ToolCall,
    ToolDefinition,
    Verbosity,
)
from app.providers.text_repair import repair_strings_in


class OpenAILLM:
    """``LLMProvider`` backed by ``client.chat.completions.create``."""

    def __init__(self, *, api_key: str, model: str, timeout: float) -> None:
        if not api_key:
            raise ProviderError("OpenAI api_key is required")
        self._client = AsyncOpenAI(api_key=api_key, timeout=timeout)
        self._model = model

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
    ) -> LLMResponse:
        params: dict[str, Any] = {
            "model": self._model,
            "messages": [_message_to_openai(m) for m in messages],
        }
        if tools:
            params["tools"] = [_tool_to_openai(t) for t in tools]
        if schema is not None:
            params["response_format"] = _schema_to_response_format(schema)
        if temperature is not None:
            params["temperature"] = temperature
        if reasoning_effort is not None:
            params["reasoning_effort"] = reasoning_effort
        if verbosity is not None:
            params["verbosity"] = verbosity
        if max_output_tokens is not None:
            # gpt-5-class reasoning models renamed `max_tokens` to
            # `max_completion_tokens`; the adapter exposes the
            # provider-agnostic name and translates here.
            params["max_completion_tokens"] = max_output_tokens

        try:
            completion = await self._client.chat.completions.create(**params)
        except APIError as exc:
            raise ProviderError(f"OpenAI API error: {exc}") from exc

        return _completion_to_response(completion, model=self._model, schema=schema)


class OpenAIEmbedder:
    """``EmbeddingProvider`` backed by ``client.embeddings.create``.

    Ships in B4 even though B6 doesn't use embeddings — keeping the
    adapter complete unblocks the hybrid-retrieval level-up (ROADMAP §
    B6 level-up).
    """

    def __init__(self, *, api_key: str, model: str, timeout: float) -> None:
        if not api_key:
            raise ProviderError("OpenAI api_key is required")
        self._client = AsyncOpenAI(api_key=api_key, timeout=timeout)
        self._model = model

    async def embed(self, texts: list[str]) -> EmbeddingResponse:
        if not texts:
            raise ProviderError("embed() requires at least one input string")
        try:
            response = await self._client.embeddings.create(
                model=self._model,
                input=texts,
                encoding_format="float",
            )
        except APIError as exc:
            raise ProviderError(f"OpenAI API error: {exc}") from exc

        vectors = [item.embedding for item in response.data]
        prompt_tokens = response.usage.prompt_tokens
        usage = TokenUsage(
            model=self._model,
            prompt_tokens=prompt_tokens,
            completion_tokens=0,
            cached_tokens=0,
            reasoning_tokens=0,
        )
        return EmbeddingResponse(vectors=vectors, usage=usage)


# ---- translators ----------------------------------------------------


def _message_to_openai(message: Message) -> dict[str, Any]:
    """Translate one provider-agnostic ``Message`` to OpenAI wire form."""
    role = message.role
    if role in {"system", "user"}:
        return {"role": role, "content": message.content or ""}
    if role == "assistant":
        out: dict[str, Any] = {"role": "assistant", "content": message.content}
        if message.tool_calls:
            out["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.name,
                        "arguments": json.dumps(tc.arguments),
                    },
                }
                for tc in message.tool_calls
            ]
        return out
    if role == "tool":
        if not message.tool_call_id:
            raise ProviderError("tool messages require tool_call_id")
        return {
            "role": "tool",
            "tool_call_id": message.tool_call_id,
            "content": message.content or "",
        }
    raise ProviderError(f"unknown message role: {role!r}")


def _tool_to_openai(tool: ToolDefinition) -> dict[str, Any]:
    """Translate a ``ToolDefinition`` to OpenAI's ``tools[]`` shape, strict."""
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.parameters,
            "strict": True,
        },
    }


def _schema_to_response_format(schema: StructuredOutputSchema) -> dict[str, Any]:
    """Translate to OpenAI ``response_format`` for strict JSON schema."""
    return {
        "type": "json_schema",
        "json_schema": {
            "name": schema.name,
            "strict": True,
            "schema": schema.json_schema,
        },
    }


def _completion_to_response(
    completion: Any,
    *,
    model: str,
    schema: StructuredOutputSchema | None,
) -> LLMResponse:
    """Translate one OpenAI ``ChatCompletion`` to ``LLMResponse``."""
    if not completion.choices:
        raise ProviderError("OpenAI response had no choices")
    choice = completion.choices[0]
    message = choice.message

    tool_calls: list[ToolCall] = []
    for raw in getattr(message, "tool_calls", None) or []:
        try:
            arguments = json.loads(raw.function.arguments or "{}")
        except json.JSONDecodeError as exc:
            raise ProviderError(
                f"tool call {raw.function.name!r} returned invalid JSON arguments"
            ) from exc
        tool_calls.append(
            ToolCall(
                id=raw.id,
                name=raw.function.name,
                arguments=repair_strings_in(arguments),
            )
        )

    content: str | None = message.content
    parsed: dict[str, Any] | None = None
    if schema is not None and content is not None and not tool_calls:
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as exc:
            # Strict mode should make this unreachable — surface loudly if it does.
            raise ProviderError(
                "OpenAI returned content that did not match the requested JSON schema"
            ) from exc
        parsed = repair_strings_in(parsed)

    usage_obj = completion.usage
    prompt_tokens = getattr(usage_obj, "prompt_tokens", 0) or 0
    completion_tokens = getattr(usage_obj, "completion_tokens", 0) or 0
    cached_tokens = 0
    prompt_details = getattr(usage_obj, "prompt_tokens_details", None)
    if prompt_details is not None:
        cached_tokens = getattr(prompt_details, "cached_tokens", 0) or 0
    reasoning_tokens = 0
    completion_details = getattr(usage_obj, "completion_tokens_details", None)
    if completion_details is not None:
        reasoning_tokens = getattr(completion_details, "reasoning_tokens", 0) or 0

    usage = TokenUsage(
        model=model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        cached_tokens=cached_tokens,
        reasoning_tokens=reasoning_tokens,
    )

    finish_reason = _map_finish_reason(getattr(choice, "finish_reason", None))

    return LLMResponse(
        content=content,
        tool_calls=tool_calls,
        parsed=parsed,
        usage=usage,
        finish_reason=finish_reason,
    )


def _map_finish_reason(raw: str | None) -> FinishReason:
    if raw in ("stop", "tool_calls", "length", "content_filter"):
        return cast(FinishReason, raw)
    return "other"
