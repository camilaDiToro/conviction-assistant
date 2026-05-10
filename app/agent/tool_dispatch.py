"""Dispatch one tool call from the LLM to the registered Python function.

The agent loop's only entry point is :func:`execute_tool`. Domain errors
raised by tools are caught and returned as a string the model can act on
(typically by retrying with corrected arguments). Non-domain exceptions
propagate.
"""

import json
from datetime import date
from typing import Any

from pydantic import BaseModel

from app.agent.tools import TOOLS, ToolContext
from app.errors import DomainError
from app.providers import ToolCall


async def execute_tool(call: ToolCall, ctx: ToolContext) -> str:
    """Dispatch one tool call; return JSON-stringified result or error."""
    entry = TOOLS.get(call.name)
    if entry is None:
        available = ", ".join(sorted(TOOLS.keys()))
        return _error_payload(f"Tool {call.name!r} does not exist. Available tools: {available}")

    try:
        result = await entry.func(ctx, **call.arguments)
    except TypeError as exc:
        return _error_payload(f"Tool {call.name!r} called with bad arguments: {exc}")
    except DomainError as exc:
        return _error_payload(f"{type(exc).__name__}: {exc}")

    return _serialize_result(result)


def _serialize_result(result: Any) -> str:
    if isinstance(result, BaseModel):
        return result.model_dump_json()
    if isinstance(result, list):
        return json.dumps([_to_jsonable(item) for item in result], default=_default_jsonable)
    return json.dumps(_to_jsonable(result), default=_default_jsonable)


def _to_jsonable(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    return value


def _default_jsonable(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, date):
        return value.isoformat()
    raise TypeError(f"object of type {type(value).__name__} is not JSON serializable")


def _error_payload(message: str) -> str:
    return json.dumps({"error": message})


__all__ = ["execute_tool"]
