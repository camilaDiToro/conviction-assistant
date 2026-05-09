"""Tests for app/providers/stub.py — fixture-driven canned responses."""

from pathlib import Path

import pytest

from app.providers.base import (
    LLMResponse,
    Message,
    ProviderError,
    StructuredOutputSchema,
    TokenUsage,
    ToolCall,
    ToolDefinition,
)
from app.providers.stub import StubEmbedder, StubLLM, load_stub_responses

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "stub_responses_example.yaml"


def _usage(prompt: int = 10, completion: int = 5) -> TokenUsage:
    return TokenUsage(
        model="stub-llm",
        prompt_tokens=prompt,
        completion_tokens=completion,
        cached_tokens=0,
    )


async def test_stub_llm_returns_canned_responses_in_order():
    first = LLMResponse(
        tool_calls=[ToolCall(id="c1", name="search_convictions", arguments={"q": "a"})],
        usage=_usage(),
        finish_reason="tool_calls",
    )
    second = LLMResponse(
        content='{"answer": "ok"}',
        parsed={"answer": "ok"},
        usage=_usage(),
    )
    stub = StubLLM([first, second])

    r1 = await stub.generate([Message(role="user", content="hi")])
    r2 = await stub.generate([Message(role="user", content="more")])

    assert r1 is first
    assert r2 is second
    assert len(stub.calls) == 2
    assert stub.calls[0].messages[0].content == "hi"
    assert stub.calls[1].messages[0].content == "more"


async def test_stub_llm_records_tools_and_schema_per_call():
    schema = StructuredOutputSchema(name="answer", json_schema={"type": "object"})
    tool = ToolDefinition(name="search", description="search", parameters={"type": "object"})
    stub = StubLLM([LLMResponse(content="ok", usage=_usage())])

    await stub.generate(
        [Message(role="user", content="hi")],
        tools=[tool],
        schema=schema,
        reasoning_effort="low",
        verbosity="low",
        max_output_tokens=200,
    )

    call = stub.calls[0]
    assert call.tools == [tool]
    assert call.schema == schema
    assert call.temperature is None
    assert call.reasoning_effort == "low"
    assert call.verbosity == "low"
    assert call.max_output_tokens == 200


async def test_stub_llm_exhausted_raises():
    stub = StubLLM([])
    with pytest.raises(ProviderError, match="exhausted"):
        await stub.generate([Message(role="user", content="hi")])


def test_load_stub_responses_yaml_roundtrip():
    responses = load_stub_responses(FIXTURE)
    assert len(responses) == 2

    first, second = responses
    assert first.finish_reason == "tool_calls"
    assert first.tool_calls and first.tool_calls[0].name == "search_convictions"
    assert first.tool_calls[0].arguments == {"query": "CDB tributação", "k": 5}

    assert second.finish_reason == "stop"
    assert second.parsed == {
        "kind": "answer",
        "answer": "CDBs follow the regressive IR table.",
        "citations": [],
    }
    assert second.usage.cached_tokens == 60


def test_load_stub_responses_rejects_non_list(tmp_path: Path):
    bad = tmp_path / "bad.yaml"
    bad.write_text("not_a_list: true\n", encoding="utf-8")
    with pytest.raises(ProviderError, match="must be a YAML list"):
        load_stub_responses(bad)


async def test_stub_embedder_default_vectors_match_input_count():
    embedder = StubEmbedder()
    response = await embedder.embed(["a", "b", "c"])
    assert len(response.vectors) == 3
    assert all(len(v) == 3 for v in response.vectors)
    assert embedder.calls == [["a", "b", "c"]]


async def test_stub_embedder_custom_vectors_and_usage():
    usage = TokenUsage(
        model="stub-embed",
        prompt_tokens=42,
        completion_tokens=0,
        cached_tokens=0,
    )
    embedder = StubEmbedder(vectors=[[0.1, 0.2], [0.3, 0.4]], usage_per_call=usage)
    response = await embedder.embed(["x", "y"])
    assert response.vectors == [[0.1, 0.2], [0.3, 0.4]]
    assert response.usage.prompt_tokens == 42


async def test_stub_embedder_empty_input_raises():
    embedder = StubEmbedder()
    with pytest.raises(ProviderError):
        await embedder.embed([])


async def test_stub_embedder_vector_count_mismatch_raises():
    embedder = StubEmbedder(vectors=[[1.0]])
    with pytest.raises(ProviderError, match="configured 1 vectors"):
        await embedder.embed(["a", "b"])
