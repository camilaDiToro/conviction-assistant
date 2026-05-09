"""SQLAlchemy ORM models."""

from app.models.base import Base
from app.models.passage import PassageORM

__all__ = ["Base", "PassageORM"]
