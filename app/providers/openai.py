"""OpenAI adapter — direct ``openai`` SDK calls.

Only this module imports the ``openai`` SDK; the rest of the project
talks to providers through ``app.providers.base``.

Tuning kwargs (``temperature``, ``reasoning_effort``, ``verbosity``,
``max_output_tokens``) are forwarded to the API only when non-``None``
— this is what keeps the adapter compatible with reasoning models like
gpt-5, which reject explicit ``temperature``.

**Prompt caching is provider-automatic** for both APIs used here. OpenAI
caches identical prefixes ≥ 1024 tokens for an hour at no opt-in cost;
``cached_tokens`` flows back through ``usage.prompt_tokens_details``
(chat completions) or ``usage.input_tokens_details`` (responses), and
both translators surface it on :class:`TokenUsage`. The caller's job is
to keep the stable system prompt at the start of the message list — see
``app.agent.loop._build_initial_messages``.
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
        effective_effort: ReasoningEffort | None = None
        if reasoning_effort is not None and _supports_reasoning_effort(self._model):
            params["reasoning_effort"] = reasoning_effort
            effective_effort = reasoning_effort
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

        return _completion_to_response(
            completion,
            model=self._model,
            schema=schema,
            reasoning_effort=effective_effort,
        )


class OpenAIResponsesLLM:
    """``LLMProvider`` backed by ``client.responses.create``.

    Required for the gpt-5.4 / gpt-5.5 family — OpenAI rejected function
    tools + reasoning_effort on /v1/chat/completions for those models
    (400 "Please use /v1/responses instead"). For earlier reasoning
    models (gpt-5, gpt-5.1, o-series) and all non-reasoning chat
    models, ``OpenAILLM`` (chat completions) is still used; the factory
    routes by model name.

    The wire shape differs in five places vs chat completions:

    1. ``messages`` → ``input`` of items: ``{type:"message",role,content}``,
       ``{type:"function_call",call_id,name,arguments}`` (assistant tool
       request), ``{type:"function_call_output",call_id,output}`` (tool
       result — replaces the ``role:"tool"`` message).
    2. Tools: flat ``{type:"function",name,description,parameters,strict}``
       (no nested ``function`` key like chat).
    3. Structured output: ``text.format`` (not ``response_format``).
    4. Reasoning: ``reasoning={"effort":...}`` (not top-level).
    5. Output: ``response.output`` is an array of items; each item is a
       ``function_call`` or a ``message`` with content parts. We walk
       it and lift the JSON text + tool calls back into ``LLMResponse``.
    """

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
        # temperature/verbosity are not honoured by Responses-API reasoning
        # models, so we drop them silently rather than forwarding.

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


class OpenAIEmbedder:
    """``EmbeddingProvider`` backed by ``client.embeddings.create``.

    Ships even though current retrieval doesn't use embeddings — keeping
    the adapter complete unblocks the hybrid-retrieval level-up.
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


# ---- model capability gates ---------------------------------------


def _supports_reasoning_effort(model: str) -> bool:
    """True when the model accepts the ``reasoning_effort`` param.

    Non-reasoning chat models (gpt-4o, gpt-4.1, gpt-3.5, gpt-4) reject
    it (400 "Unrecognized request argument"). Reasoning families —
    gpt-5 and its successors (gpt-5.1+, gpt-5.4-mini, gpt-5.5, …) and
    the o-series (o1/o3/o4) — accept it. Prefix matching so version
    suffixes (e.g. ``gpt-5-mini-2025-10``) keep working.
    """
    name = model.lower()
    if name.startswith("gpt-5"):
        return True
    return name.startswith(("o1", "o3", "o4"))


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
    reasoning_effort: ReasoningEffort | None = None,
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

    # Hoist usage + finish_reason above the parse block so the
    # empty-output error can name the actual cause (reasoning ate the
    # max_completion_tokens budget) instead of falling back to the
    # generic "did not match the requested JSON schema" message.
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
        reasoning_effort=reasoning_effort,
    )
    finish_reason = _map_finish_reason(getattr(choice, "finish_reason", None))

    content: str | None = message.content
    parsed: dict[str, Any] | None = None
    if schema is not None and not tool_calls:
        # Empty content with finish_reason=length means reasoning tokens
        # consumed the whole max_completion_tokens budget — gpt-5 at
        # medium effort routinely needs 4-5k reasoning tokens on broad
        # synthesis turns alone. The generic schema error hid this; here
        # we name the cause and the actionable knob.
        if content is None or not content.strip():
            if finish_reason == "length":
                raise ProviderError(
                    f"OpenAI truncated output before producing structured JSON "
                    f"(finish_reason=length, completion_tokens={completion_tokens}, "
                    f"reasoning_tokens={reasoning_tokens}). Raise "
                    f"AGENT_MAX_OUTPUT_TOKENS or lower AGENT_REASONING_EFFORT."
                )
            raise ProviderError(
                f"OpenAI returned empty content (finish_reason={finish_reason!r}) "
                f"and no tool calls; cannot decode against schema {schema.name!r}."
            )
        # Strict mode should give us a single JSON object, but gpt-5
        # occasionally appends a trailing object or stray text after the
        # first object — json.loads then raises "Extra data". Use
        # raw_decode to take the first complete JSON value and discard
        # any tail, falling back to a hard error if even the first value
        # is unparseable.
        try:
            parsed, _ = json.JSONDecoder().raw_decode(content.lstrip())
        except json.JSONDecodeError as exc:
            raise ProviderError(
                "OpenAI returned content that did not match the requested JSON schema"
            ) from exc
        parsed = repair_strings_in(parsed)

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


# ---- Responses API translators ------------------------------------


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
                # One function_call item per tool call. Text content (if
                # any) is emitted as a separate message item alongside.
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
                # output_text is the standard part type for text content
                # in a Responses message item.
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
