"""GET /api/config — surface the server-selected chat model."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict

from app.api.auth import require_chat_token
from app.config import settings

router = APIRouter(tags=["config"])


class ConfigResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model: str


@router.get(
    "/config",
    response_model=ConfigResponse,
    dependencies=[Depends(require_chat_token)],
)
async def get_config() -> ConfigResponse:
    return ConfigResponse(model=settings.openai_model)


__all__ = ["router"]
