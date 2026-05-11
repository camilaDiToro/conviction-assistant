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

    llm_provider: Literal["openai", "anthropic"] = "openai"
    openai_api_key: str | None = None
    openai_model: str = "gpt-5.5"
    openai_timeout_seconds: float = 60.0

    # Agent loop tuning.
    agent_max_tool_calls: int = 5
    agent_max_iterations: int = 12
    agent_max_output_tokens: int = 8192
    # Only the values supported by every model in the factory allowlist:
    # gpt-5.4 supports "minimal" but gpt-5.5 dropped it; gpt-5.5 supports
    # "none" but gpt-5.4 does not; o4-mini supports neither. The safe
    # intersection is low/medium/high.
    agent_reasoning_effort: Literal["low", "medium", "high"] = "low"
    rewrite_max_output_tokens: int = 200
    rewrite_reasoning_effort: Literal["low", "medium", "high"] = "low"
    retrieval_strategy: Literal["bm25"] = "bm25"

    chat_access_token: str | None = None
    admin_token: str | None = None

    # Deploy. On Hugging Face Spaces' free tier the filesystem is ephemeral,
    # so the SQLite DB is empty after every cold start and the corpus must be
    # re-ingested. When this is true the lifespan calls ingest_corpus() if the
    # passages table is empty. Default off keeps tests and local dev unchanged.
    auto_ingest_on_startup: bool = False

    @property
    def async_database_url(self) -> str:
        return f"sqlite+aiosqlite:///{self.sqlite_path.as_posix()}"

    @property
    def sync_database_url(self) -> str:
        # Used by Alembic only — Alembic doesn't support async drivers.
        return f"sqlite:///{self.sqlite_path.as_posix()}"


settings = Settings()
