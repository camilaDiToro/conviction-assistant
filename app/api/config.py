"""GET /api/config — surface server defaults + allowed override values.

Read-only endpoint the frontend uses to populate the Settings drawer:
defaults to display, allowed values for dropdowns, numeric bounds for
sliders. Gated by ``X-Chat-Token`` (same gate as ``/chat``) — the user
that already passed the access gate can see the config; no admin token
needed.

Bounds here MUST match the ``Field(ge=..., le=...)`` constraints in
``app/api/schemas.py::ChatOverrides``. The frontend trusts these bounds
to keep slider inputs inside the validation surface.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict

from app.api.auth import require_chat_token
from app.config import settings

router = APIRouter(tags=["config"])


class IntBounds(BaseModel):
    model_config = ConfigDict(extra="forbid")

    min: int
    max: int


class ConfigDefaults(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model: str
    reasoning_effort: str
    rewrite_reasoning_effort: str
    agent_max_tool_calls: int
    agent_max_iterations: int
    agent_max_output_tokens: int


class ConfigResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    defaults: ConfigDefaults
    allowed_models: list[str]
    allowed_reasoning_efforts: list[str]
    limits: dict[str, IntBounds]


@router.get(
    "/config",
    response_model=ConfigResponse,
    dependencies=[Depends(require_chat_token)],
)
async def get_config() -> ConfigResponse:
    return ConfigResponse(
        defaults=ConfigDefaults(
            model=settings.openai_model,
            reasoning_effort=settings.agent_reasoning_effort,
            rewrite_reasoning_effort=settings.rewrite_reasoning_effort,
            agent_max_tool_calls=settings.agent_max_tool_calls,
            agent_max_iterations=settings.agent_max_iterations,
            agent_max_output_tokens=settings.agent_max_output_tokens,
        ),
        allowed_models=list(settings.allowed_models),
        allowed_reasoning_efforts=["none", "minimal", "low", "medium", "high", "xhigh"],
        limits={
            "agent_max_tool_calls": IntBounds(min=1, max=10),
            "agent_max_output_tokens": IntBounds(min=256, max=16384),
        },
    )


__all__ = ["router"]
