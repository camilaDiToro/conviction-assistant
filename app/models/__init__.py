"""SQLAlchemy ORM models.

`Base` is the declarative base; tables are declared in dedicated modules.
Schema is owned by Alembic — `alembic/versions/` is the source of truth on
disk. These models exist for typed query construction (select(PassageORM)…)
and as the eventual source for `--autogenerate` once every table has an
ORM model (audit_log lands in B9).
"""

from app.models.base import Base
from app.models.passage import PassageORM

__all__ = ["Base", "PassageORM"]
