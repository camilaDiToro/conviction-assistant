"""Application settings."""

from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "decade-ai-challenge"
    sqlite_path: Path = Path("data/conviction_assistant.sqlite")
    convictions_dir: Path = Path("convictions")

    # Provider config (B4). Tests use StubLLM directly (factory-bypassed).
    llm_provider: Literal["openai", "anthropic"] = "openai"
    openai_api_key: str | None = None
    openai_model: str = "gpt-5"
    openai_embedding_model: str = "text-embedding-3-large"
    openai_timeout_seconds: float = 60.0

    # Agent loop tuning (B7). Read by app/agent/loop.py and app/agent/rewrite.py.
    # Override from .env without code changes — ALL CAPS variable names.
    agent_max_tool_calls: int = 5
    agent_max_iterations: int = 12
    agent_max_output_tokens: int = 4096
    agent_reasoning_effort: Literal["minimal", "low", "medium", "high"] = "low"
    rewrite_max_output_tokens: int = 200
    rewrite_reasoning_effort: Literal["minimal", "low", "medium", "high"] = "minimal"

    @property
    def async_database_url(self) -> str:
        return f"sqlite+aiosqlite:///{self.sqlite_path.as_posix()}"

    @property
    def sync_database_url(self) -> str:
        # Used by Alembic only — Alembic doesn't support async drivers.
        return f"sqlite:///{self.sqlite_path.as_posix()}"


settings = Settings()
