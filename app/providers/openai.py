"""OpenAI adapter — direct ``openai`` SDK calls via the Responses API.

Only this module imports the ``openai`` SDK; the rest of the project
talks to providers through ``app.providers.base``.

The adapter targets ``/v1/responses`` exclusively. The factory enforces
an allowlist of supported models (see ``factory.py``). The wire shape
of the Responses API differs from chat completions in five places:

1. ``messages`` → ``input`` of items: ``{type:"message",role,content}``,
   ``{type:"function_call",call_id,name,arguments}`` (assistant tool
   request), ``{type:"function_call_output",call_id,output}`` (tool
   result — replaces the ``role:"tool"`` message).
2. Tools: flat ``{type:"function",name,description,parameters,strict}``
   (no nested ``function`` key like chat completions).
3. Structured output: ``text.format`` (not ``response_format``).
4. Reasoning: ``reasoning={"effort":...}`` (not top-level).
5. Output: ``response.output`` is an array of items; each item is a
   ``function_call`` or a ``message`` with content parts. We walk it
   and lift the JSON text + tool calls back into ``LLMResponse``.

**Prompt caching is provider-automatic.** OpenAI caches identical
prefixes ≥ 1024 tokens for an hour at no opt-in cost; ``cached_tokens``
flows back through ``usage.input_tokens_details`` and is surfaced on
``TokenUsage``. The caller's job is to keep the stable system prompt at
the start of the message list — see ``app.agent.loop._build_initial_messages``.
"""

import json
from typing import Any

from openai import APIError, AsyncOpenAI

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
from app.providers.text_repair import repair_strings_in


class OpenAILLM:
    """``LLMProvider`` backed by ``client.responses.create``."""

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
        reasoning_effort: ReasoningEffort | None = None,
        max_output_tokens: int | None = None,
    ) -> LLMResponse:
        instructions, input_items = _messages_to_responses_input(messages)
        params: dict[str, Any] = {
            "model": self._model,
            "input": input_items,
        }
        if instructions is not None:
            params["instructions"] = instructions
        if tools:
            params["tools"] = [_tool_to_responses(t) for t in tools]
        if schema is not None:
            params["text"] = {"format": _schema_to_responses_format(schema)}
        if reasoning_effort is not None:
            params["reasoning"] = {"effort": reasoning_effort}
        if max_output_tokens is not None:
            params["max_output_tokens"] = max_output_tokens

        try:
            response = await self._client.responses.create(**params)
        except APIError as exc:
            raise ProviderError(f"OpenAI API error: {exc}") from exc

        return _response_to_llm_response(
            response,
            model=self._model,
            schema=schema,
            reasoning_effort=reasoning_effort,
        )


# ---- translators ---------------------------------------------------


def _messages_to_responses_input(
    messages: list[Message],
) -> tuple[str | None, list[dict[str, Any]]]:
    """Translate provider-agnostic ``Message`` list to Responses input.

    Returns ``(instructions, input_items)``. The first system message is
    hoisted to top-level ``instructions`` (the Responses API's idiomatic
    spot for it); any later system messages are inlined as
    ``{type:"message",role:"system"}`` items.
    """
    instructions: str | None = None
    items: list[dict[str, Any]] = []
    for msg in messages:
        role = msg.role
        if role == "system":
            if instructions is None:
                instructions = msg.content or ""
                continue
            items.append({"type": "message", "role": "system", "content": msg.content or ""})
        elif role == "user":
            items.append({"type": "message", "role": "user", "content": msg.content or ""})
        elif role == "assistant":
            if msg.tool_calls:
                if msg.content:
                    items.append({"type": "message", "role": "assistant", "content": msg.content})
                for tc in msg.tool_calls:
                    items.append(
                        {
                            "type": "function_call",
                            "call_id": tc.id,
                            "name": tc.name,
                            "arguments": json.dumps(tc.arguments),
                        }
                    )
            else:
                items.append({"type": "message", "role": "assistant", "content": msg.content or ""})
        elif role == "tool":
            if not msg.tool_call_id:
                raise ProviderError("tool messages require tool_call_id")
            items.append(
                {
                    "type": "function_call_output",
                    "call_id": msg.tool_call_id,
                    "output": msg.content or "",
                }
            )
        else:
            raise ProviderError(f"unknown message role: {role!r}")
    return instructions, items


def _tool_to_responses(tool: ToolDefinition) -> dict[str, Any]:
    """Translate a ``ToolDefinition`` to Responses' flat function-tool shape."""
    return {
        "type": "function",
        "name": tool.name,
        "description": tool.description,
        "parameters": tool.parameters,
        "strict": True,
    }


def _schema_to_responses_format(schema: StructuredOutputSchema) -> dict[str, Any]:
    """Translate to Responses' ``text.format`` for strict JSON schema."""
    return {
        "type": "json_schema",
        "name": schema.name,
        "strict": True,
        "schema": schema.json_schema,
    }


def _response_to_llm_response(
    response: Any,
    *,
    model: str,
    schema: StructuredOutputSchema | None,
    reasoning_effort: ReasoningEffort | None = None,
) -> LLMResponse:
    """Translate one Responses-API ``Response`` to ``LLMResponse``.

    Walks ``response.output`` collecting function_call items and the
    text content of message items. When a schema was requested the
    aggregated text content is parsed as JSON.
    """
    tool_calls: list[ToolCall] = []
    content_chunks: list[str] = []
    for item in getattr(response, "output", None) or []:
        item_type = getattr(item, "type", None)
        if item_type == "function_call":
            try:
                arguments = json.loads(getattr(item, "arguments", None) or "{}")
            except json.JSONDecodeError as exc:
                raise ProviderError(
                    f"tool call {getattr(item, 'name', '<unknown>')!r} "
                    f"returned invalid JSON arguments"
                ) from exc
            tool_calls.append(
                ToolCall(
                    id=getattr(item, "call_id", "") or "",
                    name=getattr(item, "name", "") or "",
                    arguments=repair_strings_in(arguments),
                )
            )
        elif item_type == "message":
            for part in getattr(item, "content", None) or []:
                part_type = getattr(part, "type", None)
                if part_type in ("output_text", "text"):
                    text = getattr(part, "text", None)
                    if text:
                        content_chunks.append(text)
        # ignore reasoning items, refusals, etc. (not load-bearing here)

    usage_obj = getattr(response, "usage", None)
    input_tokens = getattr(usage_obj, "input_tokens", 0) or 0
    output_tokens = getattr(usage_obj, "output_tokens", 0) or 0
    cached_tokens = 0
    input_details = getattr(usage_obj, "input_tokens_details", None)
    if input_details is not None:
        cached_tokens = getattr(input_details, "cached_tokens", 0) or 0
    reasoning_tokens = 0
    output_details = getattr(usage_obj, "output_tokens_details", None)
    if output_details is not None:
        reasoning_tokens = getattr(output_details, "reasoning_tokens", 0) or 0

    usage = TokenUsage(
        model=model,
        prompt_tokens=input_tokens,
        completion_tokens=output_tokens,
        cached_tokens=cached_tokens,
        reasoning_tokens=reasoning_tokens,
        reasoning_effort=reasoning_effort,
    )

    status = getattr(response, "status", None)
    incomplete = getattr(response, "incomplete_details", None)
    finish_reason = _responses_status_to_finish_reason(status, incomplete, tool_calls)

    content_text = "".join(content_chunks) if content_chunks else None
    parsed: dict[str, Any] | None = None
    if schema is not None and not tool_calls:
        if not content_text or not content_text.strip():
            if finish_reason == "length":
                raise ProviderError(
                    f"OpenAI truncated output before producing structured JSON "
                    f"(status=incomplete, output_tokens={output_tokens}, "
                    f"reasoning_tokens={reasoning_tokens}). Raise "
                    f"AGENT_MAX_OUTPUT_TOKENS or lower AGENT_REASONING_EFFORT."
                )
            raise ProviderError(
                f"OpenAI returned empty content (finish_reason={finish_reason!r}) "
                f"and no tool calls; cannot decode against schema {schema.name!r}."
            )
        try:
            parsed, _ = json.JSONDecoder().raw_decode(content_text.lstrip())
        except json.JSONDecodeError as exc:
            raise ProviderError(
                "OpenAI returned content that did not match the requested JSON schema"
            ) from exc
        parsed = repair_strings_in(parsed)

    return LLMResponse(
        content=content_text,
        tool_calls=tool_calls,
        parsed=parsed,
        usage=usage,
        finish_reason=finish_reason,
    )


def _responses_status_to_finish_reason(
    status: str | None,
    incomplete: Any,
    tool_calls: list[ToolCall],
) -> FinishReason:
    """Map Responses-API ``status`` (+ ``incomplete_details``) to the
    chat-completions-style ``FinishReason`` our orchestrator already
    knows how to handle."""
    if status == "completed":
        return "tool_calls" if tool_calls else "stop"
    if status == "incomplete":
        reason = getattr(incomplete, "reason", None) if incomplete is not None else None
        if reason == "max_output_tokens":
            return "length"
        if reason == "content_filter":
            return "content_filter"
        return "other"
    return "other"
