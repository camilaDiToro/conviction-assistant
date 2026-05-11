"""Alembic bootstrap.

The app is async (aiosqlite), but Alembic itself runs through the sync
SQLite driver: `db.migrate()` builds a `sqlite:///…` URL and calls the
sync `command.upgrade` API at lifespan startup. That's fine for SQLite v1.
When the project moves to Postgres+asyncpg, switch to the async cookbook
pattern (``async_engine_from_config`` + ``connection.run_sync``).

``target_metadata`` is wired to ``Base.metadata`` so ``alembic revision
--autogenerate`` would catch ORM↔schema drift. We still author migrations
by hand — autogenerate is a safety net, not the workflow.
"""

from sqlalchemy import engine_from_config, pool

from alembic import context
# Importing the package side-effect-registers every ORM model on Base.metadata.
from app.models import Base

config = context.config
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=connection.dialect.name == "sqlite",
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
