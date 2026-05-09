"""Alembic environment for the Decade conviction assistant.

We don't use SQLAlchemy ORM models — migrations are imperative
(op.create_table / op.execute on raw SQL). target_metadata stays None;
autogenerate is therefore not supported, which is intentional.

The `alembic/` directory is the schema-of-record for the store/ layer.
SQLite-specific render_as_batch is enabled so future ALTER-style migrations
work despite SQLite's limitations.
"""

from sqlalchemy import engine_from_config, pool

from alembic import context

config = context.config
target_metadata = None


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
