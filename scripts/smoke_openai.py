"""Manual smoke test for the OpenAI adapter.

1. Round-trips a text generation through `generate()` (no schema).
2. Round-trips a structured-output generation against a strict JSON
   schema.
3. Round-trips a tool-calling request and surfaces the tool call.
4. Round-trips an embedding call.
"""

import asyncio
import os
import sys

from dotenv import load_dotenv

from app.providers.base import (
    Message,
    StructuredOutputSchema,
    ToolDefinition,
)
from app.providers.openai import OpenAIEmbedder, OpenAILLM

load_dotenv()


async def _smoke() -> None:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("OPENAI_API_KEY is required", file=sys.stderr)
        raise SystemExit(2)

    model = os.environ.get("OPENAI_MODEL", "gpt-5")
    embedding_model = os.environ.get("OPENAI_EMBEDDING_MODEL", "text-embedding-3-large")

    llm = OpenAILLM(api_key=api_key, model=model, timeout=60.0)
    embedder = OpenAIEmbedder(api_key=api_key, model=embedding_model, timeout=60.0)

    print(f"--- {model} text generation ---")
    text = await llm.generate(
        [
            Message(role="system", content="You are a terse assistant."),
            Message(role="user", content="What is 2 + 2? Reply with just the number."),
        ],
        reasoning_effort="low",
    )
    print(f"  content={text.content!r}")
    print(f"  usage={text.usage.model_dump()}")

    print(f"\n--- {model} structured output (strict JSON schema) ---")
    schema = StructuredOutputSchema(
        name="city_capital",
        json_schema={
            "type": "object",
            "properties": {
                "city": {"type": "string"},
                "country": {"type": "string"},
            },
            "required": ["city", "country"],
            "additionalProperties": False,
        },
    )
    structured = await llm.generate(
        [
            Message(role="user", content="What is the capital of France? Return JSON."),
        ],
        schema=schema,
        reasoning_effort="low",
        verbosity="low",
        max_output_tokens=200,
    )
    print(f"  parsed={structured.parsed!r}")
    print(f"  usage={structured.usage.model_dump()}")

    print(f"\n--- {model} tool calling ---")
    tool = ToolDefinition(
        name="get_weather",
        description="Get the current weather for a location.",
        parameters={
            "type": "object",
            "properties": {"location": {"type": "string"}},
            "required": ["location"],
            "additionalProperties": False,
        },
    )
    tooled = await llm.generate(
        [Message(role="user", content="What's the weather in Tokyo?")],
        tools=[tool],
        reasoning_effort="low",
    )
    print(f"  tool_calls={[tc.model_dump() for tc in tooled.tool_calls]}")
    print(f"  finish_reason={tooled.finish_reason}")
    print(f"  usage={tooled.usage.model_dump()}")

    print(f"\n--- {embedding_model} embedding ---")
    emb = await embedder.embed(["OpenAI makes great APIs", "Python is a great language"])
    print(f"  vectors: {len(emb.vectors)} of length {len(emb.vectors[0])}")
    print(f"  usage={emb.usage.model_dump()}")


if __name__ == "__main__":
    asyncio.run(_smoke())
