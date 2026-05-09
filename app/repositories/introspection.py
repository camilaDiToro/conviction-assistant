"""Schema introspection helpers.

Lives in `app/repositories/` because these functions run SQL (per
layering rule #1: no SQL outside repositories). Used by tests to assert
the schema bootstrap landed; B9 may use them for the audit-log writer's
self-check.
"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def list_tables(session: AsyncSession) -> set[str]:
    """User tables in the connected database (includes alembic_version)."""
    result = await session.execute(
        text("SELECT name FROM sqlite_master WHERE type='table'")
    )
    return set(result.scalars().all())


async def list_views(session: AsyncSession) -> set[str]:
    """Views in the connected database."""
    result = await session.execute(
        text("SELECT name FROM sqlite_master WHERE type='view'")
    )
    return set(result.scalars().all())
