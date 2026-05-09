"""Tests for app/providers/openai.py — translators + adapter call shape.

The adapter's HTTP path is exercised manually via
``scripts/smoke_openai.py``. CI never hits real OpenAI — we mock the
``AsyncOpenAI`` client's ``create`` methods and assert on the arguments
passed plus the ``LLMResponse`` we build from a fake completion.
"""

import json
from types import SimpleNamespace
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
    OpenAIEmbedder,
    OpenAILLM,
    _completion_to_response,
    _message_to_openai,
    _schema_to_response_format,
    _tool_to_openai,
)


def test_message_to_openai_system_user():
    assert _message_to_openai(Message(role="system", content="be terse")) == {
        "role": "system",
        "content": "be terse",
    }
    assert _message_to_openai(Message(role="user", content="hi")) == {
        "role": "user",
        "content": "hi",
    }


def test_message_to_openai_assistant_text():
    out = _message_to_openai(Message(role="assistant", content="ok"))
    assert out == {"role": "assistant", "content": "ok"}


def test_message_to_openai_assistant_tool_calls():
    msg = Message(
        role="assistant",
        content=None,
        tool_calls=[ToolCall(id="c1", name="search", arguments={"q": "x", "k": 5})],
    )
    out = _message_to_openai(msg)
    assert out["role"] == "assistant"
    assert out["content"] is None
    assert out["tool_calls"][0]["id"] == "c1"
    assert out["tool_calls"][0]["type"] == "function"
    assert json.loads(out["tool_calls"][0]["function"]["arguments"]) == {"q": "x", "k": 5}


def test_message_to_openai_tool_result():
    out = _message_to_openai(Message(role="tool", tool_call_id="c1", content="result text"))
    assert out == {"role": "tool", "tool_call_id": "c1", "content": "result text"}


def test_message_to_openai_tool_without_id_raises():
    with pytest.raises(ProviderError, match="tool_call_id"):
        _message_to_openai(Message(role="tool", content="x"))


def test_tool_to_openai_marks_strict():
    tool = ToolDefinition(
        name="search",
        description="search the corpus",
        parameters={"type": "object", "properties": {}, "additionalProperties": False},
    )
    out = _tool_to_openai(tool)
    assert out["type"] == "function"
    assert out["function"]["name"] == "search"
    assert out["function"]["strict"] is True
    assert out["function"]["parameters"] == tool.parameters


def test_schema_to_response_format_strict():
    schema = StructuredOutputSchema(name="answer", json_schema={"type": "object"})
    out = _schema_to_response_format(schema)
    assert out == {
        "type": "json_schema",
        "json_schema": {
            "name": "answer",
            "strict": True,
            "schema": {"type": "object"},
        },
    }


def _fake_completion(
    *,
    content: str | None,
    tool_calls: list[dict] | None = None,
    finish_reason: str = "stop",
    prompt_tokens: int = 100,
    completion_tokens: int = 10,
    cached_tokens: int = 0,
    reasoning_tokens: int = 0,
):
    """Build the minimal SDK-shaped object the translator inspects."""
    raw_tool_calls = []
    for tc in tool_calls or []:
        raw_tool_calls.append(
            SimpleNamespace(
                id=tc["id"],
                function=SimpleNamespace(name=tc["name"], arguments=json.dumps(tc["arguments"])),
            )
        )
    message = SimpleNamespace(content=content, tool_calls=raw_tool_calls or None)
    choice = SimpleNamespace(message=message, finish_reason=finish_reason)
    usage = SimpleNamespace(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        prompt_tokens_details=SimpleNamespace(cached_tokens=cached_tokens),
        completion_tokens_details=SimpleNamespace(reasoning_tokens=reasoning_tokens),
    )
    return SimpleNamespace(choices=[choice], usage=usage)


def test_completion_to_response_text_with_schema_parses():
    schema = StructuredOutputSchema(name="answer", json_schema={"type": "object"})
    completion = _fake_completion(content='{"kind":"answer","answer":"hi","citations":[]}')

    response = _completion_to_response(completion, model="gpt-5", schema=schema)

    assert response.parsed == {"kind": "answer", "answer": "hi", "citations": []}
    assert response.tool_calls == []
    assert response.finish_reason == "stop"
    assert response.usage.model == "gpt-5"
    assert response.usage.prompt_tokens == 100
    assert response.usage.completion_tokens == 10


def test_completion_to_response_tool_calls_decoded_and_parsed_skipped():
    completion = _fake_completion(
        content=None,
        tool_calls=[{"id": "c1", "name": "search", "arguments": {"q": "x"}}],
        finish_reason="tool_calls",
    )

    response = _completion_to_response(completion, model="gpt-5", schema=None)

    assert response.parsed is None
    assert response.tool_calls == [ToolCall(id="c1", name="search", arguments={"q": "x"})]
    assert response.finish_reason == "tool_calls"


def test_completion_to_response_cached_tokens_split_tiers():
    completion = _fake_completion(
        content="ok", prompt_tokens=1000, completion_tokens=10, cached_tokens=300
    )
    response = _completion_to_response(completion, model="gpt-5", schema=None)
    assert response.usage.cached_tokens == 300


def test_completion_to_response_captures_reasoning_tokens():
    completion = _fake_completion(
        content="ok", prompt_tokens=100, completion_tokens=500, reasoning_tokens=400
    )
    response = _completion_to_response(completion, model="gpt-5", schema=None)
    assert response.usage.completion_tokens == 500
    assert response.usage.reasoning_tokens == 400


def test_completion_to_response_invalid_json_raises():
    schema = StructuredOutputSchema(name="answer", json_schema={"type": "object"})
    completion = _fake_completion(content="not json")
    with pytest.raises(ProviderError, match="did not match the requested JSON schema"):
        _completion_to_response(completion, model="gpt-5", schema=schema)


def test_completion_to_response_no_choices_raises():
    completion = SimpleNamespace(choices=[], usage=SimpleNamespace())
    with pytest.raises(ProviderError, match="no choices"):
        _completion_to_response(completion, model="gpt-5", schema=None)


def test_completion_to_response_unknown_finish_reason_maps_to_other():
    completion = _fake_completion(content="ok", finish_reason="some_new_reason")
    response = _completion_to_response(completion, model="gpt-5", schema=None)
    assert response.finish_reason == "other"


# ---- adapter end-to-end with mocked OpenAI client ------------------


async def test_openai_llm_default_call_omits_tuning_kwargs():
    """Default path: no temperature, no reasoning_effort, no verbosity, no max."""
    llm = OpenAILLM(api_key="sk-test", model="gpt-5", timeout=60.0)
    fake = _fake_completion(content="ok")
    mock_create = AsyncMock(return_value=fake)
    llm._client.chat.completions.create = mock_create

    await llm.generate([Message(role="user", content="hi")])

    kwargs = mock_create.await_args.kwargs
    assert kwargs["model"] == "gpt-5"
    assert kwargs["messages"] == [{"role": "user", "content": "hi"}]
    assert "temperature" not in kwargs
    assert "reasoning_effort" not in kwargs
    assert "verbosity" not in kwargs
    assert "max_completion_tokens" not in kwargs


async def test_openai_llm_forwards_tools_and_schema():
    llm = OpenAILLM(api_key="sk-test", model="gpt-5", timeout=60.0)
    schema = StructuredOutputSchema(name="answer", json_schema={"type": "object"})
    tool = ToolDefinition(name="search", description="d", parameters={"type": "object"})

    mock_create = AsyncMock(return_value=_fake_completion(content='{"a": 1}'))
    llm._client.chat.completions.create = mock_create

    await llm.generate(
        [Message(role="user", content="hi")],
        tools=[tool],
        schema=schema,
    )

    kwargs = mock_create.await_args.kwargs
    assert kwargs["tools"][0]["function"]["name"] == "search"
    assert kwargs["response_format"]["type"] == "json_schema"
    assert kwargs["response_format"]["json_schema"]["strict"] is True


async def test_openai_llm_forwards_tuning_kwargs_when_set():
    """Each tuning kwarg lands on the wire under the right OpenAI key name."""
    llm = OpenAILLM(api_key="sk-test", model="gpt-5", timeout=60.0)
    mock_create = AsyncMock(return_value=_fake_completion(content="ok"))
    llm._client.chat.completions.create = mock_create

    await llm.generate(
        [Message(role="user", content="hi")],
        temperature=0.7,
        reasoning_effort="low",
        verbosity="low",
        max_output_tokens=200,
    )

    kwargs = mock_create.await_args.kwargs
    assert kwargs["temperature"] == 0.7
    assert kwargs["reasoning_effort"] == "low"
    assert kwargs["verbosity"] == "low"
    assert kwargs["max_completion_tokens"] == 200
    assert "max_tokens" not in kwargs  # gpt-5 renamed it


def test_openai_clients_pass_timeout_to_async_openai():
    with patch("app.providers.openai.AsyncOpenAI") as mock_async_openai:
        OpenAILLM(api_key="sk-test", model="gpt-5", timeout=42.0)
        OpenAIEmbedder(api_key="sk-test", model="text-embedding-3-large", timeout=15.0)
        assert mock_async_openai.call_args_list[0].kwargs["timeout"] == 42.0
        assert mock_async_openai.call_args_list[1].kwargs["timeout"] == 15.0


def test_openai_llm_requires_api_key():
    with pytest.raises(ProviderError, match="api_key"):
        OpenAILLM(api_key="", model="gpt-5", timeout=60.0)


async def test_openai_embedder_calls_sdk_correctly():
    embedder = OpenAIEmbedder(api_key="sk-test", model="text-embedding-3-large", timeout=60.0)
    fake_response = SimpleNamespace(
        data=[
            SimpleNamespace(embedding=[0.1, 0.2]),
            SimpleNamespace(embedding=[0.3, 0.4]),
        ],
        usage=SimpleNamespace(prompt_tokens=12),
    )
    mock_create = AsyncMock(return_value=fake_response)
    embedder._client.embeddings.create = mock_create

    result = await embedder.embed(["a", "b"])

    kwargs = mock_create.await_args.kwargs
    assert kwargs["model"] == "text-embedding-3-large"
    assert kwargs["input"] == ["a", "b"]
    assert kwargs["encoding_format"] == "float"

    assert result.vectors == [[0.1, 0.2], [0.3, 0.4]]
    assert result.usage.prompt_tokens == 12
    assert result.usage.model == "text-embedding-3-large"


async def test_openai_embedder_empty_input_raises():
    embedder = OpenAIEmbedder(api_key="sk-test", model="text-embedding-3-large", timeout=60.0)
    with pytest.raises(ProviderError, match="at least one"):
        await embedder.embed([])


def test_openai_embedder_requires_api_key():
    with pytest.raises(ProviderError, match="api_key"):
        OpenAIEmbedder(api_key="", model="text-embedding-3-large", timeout=60.0)
