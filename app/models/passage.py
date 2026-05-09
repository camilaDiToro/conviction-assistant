from sqlalchemy import Index, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class PassageORM(Base):
    """ORM model for the `passages` table.

    Schema is defined imperatively in alembic/versions/0001_initial_schema.py;
    this class exists for typed query construction (select(PassageORM)…).

    `heading_path` is JSON-encoded (SQLite has no native array type);
    `document_updated` is an ISO date string (SQLite has no native date type).
    Conversion to native Python types happens in the repository layer before
    handing values back to callers — this class deliberately stores the raw
    on-disk shape.
    """

    __tablename__ = "passages"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    document_id: Mapped[str] = mapped_column(Text, nullable=False)
    document_title: Mapped[str] = mapped_column(Text, nullable=False)
    heading: Mapped[str] = mapped_column(Text, nullable=False)
    heading_path: Mapped[str] = mapped_column(Text, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    document_updated: Mapped[str | None] = mapped_column(Text, nullable=True)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)

    __table_args__ = (
        Index("ix_passages_doc", "document_id", "ordinal"),
    )
