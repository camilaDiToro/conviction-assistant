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
    # Bumped from 4096 → 8192: at the default reasoning effort gpt-5
    # routinely overran 4096 on broad synthesis turns, leaving `content`
    # empty and triggering a silent 500. See `app/providers/openai.py`
    # for the empty-content detection.
    agent_max_output_tokens: int = 8192
    agent_reasoning_effort: Literal["minimal", "low", "medium", "high"] = "medium"
    rewrite_max_output_tokens: int = 200
    rewrite_reasoning_effort: Literal["minimal", "low", "medium", "high"] = "minimal"

    # Strategy seams. Single-member Literal today — adding a second
    # entry is a deliberate code change (register the new strategy +
    # widen the Literal), not a `.env` flip.
    retrieval_strategy: Literal["bm25"] = "bm25"

    # B9 access tokens. Loaded from .env. The chat token is what the user
    # pastes into the frontend gate; the admin token is for /admin/* and
    # is never exposed to the browser. Both are validated server-side via
    # hmac.compare_digest. Empty values keep the endpoints open in tests
    # (the test fixtures override the deps directly); production .env
    # MUST set both — see app/api/auth.py.
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
