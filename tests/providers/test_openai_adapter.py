"""Tests for app/providers/openai.py — Responses-API translators + adapter.

The HTTP path is exercised end-to-end by the eval suite (``evals/run.py``)
against real OpenAI. CI never hits real OpenAI — we mock
``AsyncOpenAI.responses.create`` and assert on the request kwargs plus
the ``LLMResponse`` built from a fake response.
"""

import json
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from app.providers.base import (
    Message,
    ProviderError,
    StructuredOutputSchema,
    ToolCall,
    ToolDefinition,
)
from app.providers.openai import (
    OpenAILLM,
    _messages_to_responses_input,
    _response_to_llm_response,
)

# ---- Message → Responses-input translator ---------------------------


def test_messages_translator_covers_every_role():
    """One round-trip covers system hoisting, user/assistant/tool, and the
    inline path for later system messages."""
    instructions, items = _messages_to_responses_input(
        [
            Message(role="system", content="be terse"),
            Message(role="user", content="hi"),
            Message(
                role="assistant",
                tool_calls=[ToolCall(id="c1", name="search", arguments={"q": "x"})],
            ),
            Message(role="tool", tool_call_id="c1", content="result"),
            Message(role="system", content="extra"),  # later systems inline as items
        ]
    )
    assert instructions == "be terse"
    assert items == [
        {"type": "message", "role": "user", "content": "hi"},
        {"type": "function_call", "call_id": "c1", "name": "search", "arguments": '{"q": "x"}'},
        {"type": "function_call_output", "call_id": "c1", "output": "result"},
        {"type": "message", "role": "system", "content": "extra"},
    ]


def test_messages_translator_tool_role_without_id_raises():
    with pytest.raises(ProviderError, match="tool_call_id"):
        _messages_to_responses_input([Message(role="tool", content="x")])


# ---- helpers --------------------------------------------------------


def _fake_response(
    *,
    content: str | None = None,
    tool_calls: list[dict] | None = None,
    status: str = "completed",
    incomplete_reason: str | None = None,
    input_tokens: int = 100,
    output_tokens: int = 10,
    cached_tokens: int = 0,
    reasoning_tokens: int = 0,
):
    """Minimal SDK-shaped Response object the translator inspects."""
    output: list[Any] = []
    if content is not None:
        output.append(
            SimpleNamespace(
                type="message",
                content=[SimpleNamespace(type="output_text", text=content)],
            )
        )
    for tc in tool_calls or []:
        output.append(
            SimpleNamespace(
                type="function_call",
                call_id=tc["id"],
                name=tc["name"],
                arguments=json.dumps(tc["arguments"]),
            )
        )
    return SimpleNamespace(
        output=output,
        usage=SimpleNamespace(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            input_tokens_details=SimpleNamespace(cached_tokens=cached_tokens),
            output_tokens_details=SimpleNamespace(reasoning_tokens=reasoning_tokens),
        ),
        status=status,
        incomplete_details=(
            SimpleNamespace(reason=incomplete_reason) if incomplete_reason is not None else None
        ),
    )


# ---- Response → LLMResponse ----------------------------------------


def test_response_text_with_schema_parses_and_reports_tokens():
    schema = StructuredOutputSchema(name="answer", json_schema={"type": "object"})
    response = _fake_response(
        content='{"kind":"answer","answer":"hi","citations":[]}',
        input_tokens=1000,
        output_tokens=500,
        cached_tokens=300,
        reasoning_tokens=400,
    )

    out = _response_to_llm_response(response, model="gpt-5.5", schema=schema)

    assert out.parsed == {"kind": "answer", "answer": "hi", "citations": []}
    assert out.finish_reason == "stop"
    assert (out.usage.prompt_tokens, out.usage.completion_tokens) == (1000, 500)
    assert (out.usage.cached_tokens, out.usage.reasoning_tokens) == (300, 400)


def test_response_tool_calls_decoded_skip_schema_parse():
    response = _fake_response(
        tool_calls=[{"id": "c1", "name": "search", "arguments": {"q": "x"}}],
    )
    out = _response_to_llm_response(response, model="gpt-5.5", schema=None)
    assert out.tool_calls == [ToolCall(id="c1", name="search", arguments={"q": "x"})]
    assert out.parsed is None
    assert out.finish_reason == "tool_calls"


def test_response_tolerates_extra_data_after_first_json_object():
    # gpt-5 occasionally trails extra junk after the first JSON object
    schema = StructuredOutputSchema(name="answer", json_schema={"type": "object"})
    response = _fake_response(content='{"answer":"hi"}\n{"trailing":"junk"}')
    out = _response_to_llm_response(response, model="gpt-5.5", schema=schema)
    assert out.parsed == {"answer": "hi"}


@pytest.mark.parametrize(
    "fake_kwargs, error_match",
    [
        ({"content": "not json"}, r"did not match the requested JSON schema"),
        (
            {
                "status": "incomplete",
                "incomplete_reason": "max_output_tokens",
                "output_tokens": 4096,
                "reasoning_tokens": 4096,
            },
            r"output_tokens=4096.*reasoning_tokens=4096.*AGENT_MAX_OUTPUT_TOKENS",
        ),
        (
            {"status": "incomplete", "incomplete_reason": "content_filter"},
            r"empty content.*content_filter",
        ),
    ],
    ids=["invalid_json", "truncated_by_max_tokens", "content_filter"],
)
def test_response_schema_decode_errors(fake_kwargs, error_match):
    schema = StructuredOutputSchema(name="answer", json_schema={"type": "object"})
    response = _fake_response(**fake_kwargs)
    with pytest.raises(ProviderError, match=error_match):
        _response_to_llm_response(response, model="gpt-5.5", schema=schema)


# ---- adapter end-to-end with mocked client -------------------------


async def test_openai_llm_default_call_only_passes_model_and_input():
    llm = OpenAILLM(api_key="sk-test", model="gpt-5.5", timeout=60.0)
    llm._client.responses.create = AsyncMock(return_value=_fake_response(content="ok"))

    await llm.generate([Message(role="user", content="hi")])

    assert llm._client.responses.create.await_args.kwargs == {
        "model": "gpt-5.5",
        "input": [{"type": "message", "role": "user", "content": "hi"}],
    }


async def test_openai_llm_full_request_shape():
    """system+tools+schema+reasoning+max_output_tokens all land on the wire."""
    llm = OpenAILLM(api_key="sk-test", model="gpt-5.5", timeout=60.0)
    llm._client.responses.create = AsyncMock(return_value=_fake_response(content='{"a":1}'))
    schema = StructuredOutputSchema(name="answer", json_schema={"type": "object"})
    tool = ToolDefinition(name="search", description="d", parameters={"type": "object"})

    await llm.generate(
        [Message(role="system", content="be terse"), Message(role="user", content="hi")],
        tools=[tool],
        schema=schema,
        reasoning_effort="low",
        max_output_tokens=200,
    )

    kwargs = llm._client.responses.create.await_args.kwargs
    assert kwargs["instructions"] == "be terse"
    assert kwargs["input"] == [{"type": "message", "role": "user", "content": "hi"}]
    assert kwargs["tools"] == [
        {
            "type": "function",
            "name": "search",
            "description": "d",
            "parameters": {"type": "object"},
            "strict": True,
        }
    ]
    assert kwargs["text"] == {
        "format": {
            "type": "json_schema",
            "name": "answer",
            "strict": True,
            "schema": {"type": "object"},
        }
    }
    assert kwargs["reasoning"] == {"effort": "low"}
    assert kwargs["max_output_tokens"] == 200


def test_openai_client_init_validates_api_key_and_timeout():
    with pytest.raises(ProviderError, match="api_key"):
        OpenAILLM(api_key="", model="gpt-5.5", timeout=60.0)
    with patch("app.providers.openai.AsyncOpenAI") as mock_async_openai:
        OpenAILLM(api_key="sk-test", model="gpt-5.5", timeout=42.0)
        assert mock_async_openai.call_args.kwargs["timeout"] == 42.0
