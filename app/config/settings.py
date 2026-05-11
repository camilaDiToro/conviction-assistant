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
    openai_embedding_model: str = "text-embedding-3-large"
    openai_timeout_seconds: float = 60.0
    # Whitelist for per-request model overrides via /chat. Any value
    # outside this list is rejected by the request schema; this is the
    # gate that prevents arbitrary models from being charged.
    # gpt-5.5 / gpt-5.4-* are routed to the /v1/responses adapter; older
    # models stay on /v1/chat/completions. The factory picks the right
    # adapter by model name (see _requires_responses_api).
    allowed_models: list[str] = [
        "gpt-5.5",
        "gpt-5.4-mini",
        "gpt-5.1",
        "gpt-5",
        "gpt-5-mini",
        "gpt-4.1",
    ]

    # Agent loop tuning.
    agent_max_tool_calls: int = 5
    agent_max_iterations: int = 12
    agent_max_output_tokens: int = 8192
    agent_reasoning_effort: Literal["none", "minimal", "low", "medium", "high", "xhigh"] = "low"
    rewrite_max_output_tokens: int = 200
    # gpt-5.5 dropped "minimal" in favor of "none"; "low" is the safest
    # default that works across the full gpt-5.x family.
    rewrite_reasoning_effort: Literal["none", "minimal", "low", "medium", "high", "xhigh"] = "low"
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
