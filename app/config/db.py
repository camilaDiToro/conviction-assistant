"""Async engine + session factory; sync Alembic migration."""

from collections.abc import AsyncIterator
from pathlib import Path

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_ALEMBIC_DIR = _REPO_ROOT / "alembic"

_session_factory: async_sessionmaker[AsyncSession] | None = None


def make_engine(database_url: str) -> AsyncEngine:
    """Create an async engine. Caller is responsible for disposing it."""
    return create_async_engine(database_url)


def make_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


def set_session_factory(factory: async_sessionmaker[AsyncSession] | None) -> None:
    """Install (or clear with None) the process-wide session factory."""
    global _session_factory
    _session_factory = factory


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency yielding a session from the configured factory."""
    if _session_factory is None:
        raise RuntimeError(
            "session factory not configured — lifespan didn't run "
            "or tests forgot to override get_session"
        )
    async with _session_factory() as session:
        yield session


def migrate(sqlite_path: str | Path) -> None:
    """Apply pending Alembic migrations to `sqlite_path`. Idempotent."""
    from alembic.config import Config

    from alembic import command

    Path(sqlite_path).parent.mkdir(parents=True, exist_ok=True)
    cfg = Config()
    cfg.set_main_option("script_location", str(_ALEMBIC_DIR))
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{Path(sqlite_path).as_posix()}")
    command.upgrade(cfg, "head")
