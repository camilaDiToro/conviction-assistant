"""Async SQLAlchemy engine + session factory; sync Alembic migration.

Lives in `app/config/` because engine setup is configuration-adjacent —
the URL, lifecycle, and alembic location are all driven by settings.
This module only constructs the engine and exposes the FastAPI Depends;
**SQL execution still belongs to `app/repositories/`** (per layering
rule #1). Schema introspection helpers live in
`app/repositories/introspection.py`.

The engine and session factory are created at app startup (lifespan in
`app/main.py`) and disposed at shutdown. Tests build their own per-test
engine via fixtures and override `get_session` via FastAPI's
dependency_overrides.

Schema is owned by Alembic — `alembic/versions/` is the source of truth
on disk. `migrate()` applies all pending migrations to the SQLite file at
the configured path; it uses Alembic's sync API because Alembic doesn't
support async drivers (which is fine — migrations are a startup concern,
not a request path).
"""

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
    return create_async_engine(database_url, future=True)


def make_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


def set_session_factory(factory: async_sessionmaker[AsyncSession] | None) -> None:
    """Install (or clear, with None) the process-wide session factory.

    Lifespan calls this on startup; tests override `get_session` via FastAPI's
    dependency_overrides instead.
    """
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
    """Apply all pending Alembic migrations to the SQLite file at `sqlite_path`.

    Creates the file (and parent directory) if needed. Idempotent.
    """
    from alembic.config import Config

    from alembic import command

    Path(sqlite_path).parent.mkdir(parents=True, exist_ok=True)
    cfg = Config()
    cfg.set_main_option("script_location", str(_ALEMBIC_DIR))
    cfg.set_main_option(
        "sqlalchemy.url", f"sqlite:///{Path(sqlite_path).as_posix()}"
    )
    command.upgrade(cfg, "head")
