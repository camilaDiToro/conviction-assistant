"""Application settings + DB plumbing.

`settings` is the only place env-var loading happens (per CLAUDE.md
hard rule #3). DB connection plumbing (engine, session factory, lifespan
helpers, alembic migrate) lives in `app/config/db.py` so engine setup
sits next to the configuration that drives it.

Note: SQL execution still belongs to `app/repositories/` — `db.py`
here only constructs the engine and exposes the FastAPI Depends.
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "decade-ai-challenge"
    env: str = "dev"
    sqlite_path: Path = Path("data/conviction_assistant.sqlite")
    convictions_dir: Path = Path("convictions")

    @property
    def async_database_url(self) -> str:
        return f"sqlite+aiosqlite:///{self.sqlite_path.as_posix()}"

    @property
    def sync_database_url(self) -> str:
        # Used by Alembic only — Alembic doesn't support async drivers.
        return f"sqlite:///{self.sqlite_path.as_posix()}"


settings = Settings()
