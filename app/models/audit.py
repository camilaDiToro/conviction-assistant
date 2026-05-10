"""ORM model for the audit_log table (B9).

The schema lives in alembic (``0001_initial_schema.py``); this ORM model
exists so the repository layer can use ``select()`` style queries
instead of raw text(). The table is append-only — there's no update path.
"""

from sqlalchemy import Index, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AuditLogORM(Base):
    __tablename__ = "audit_log"

    step_id: Mapped[str] = mapped_column(Text, primary_key=True)
    question_id: Mapped[str] = mapped_column(Text, nullable=False)
    conversation_id: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[str] = mapped_column(Text, nullable=False)
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[str] = mapped_column(Text, nullable=False)
    usage: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_audit_question", "question_id"),
        Index("ix_audit_conversation", "conversation_id"),
    )
