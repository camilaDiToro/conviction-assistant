"""ORM model for the audit_log table."""

from sqlalchemy import CheckConstraint, Index, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

# Mirror of the CHECK in alembic/versions/0001_initial_schema.py — keeps
# `target_metadata = Base.metadata` autogenerate from diffing it away.
_AUDIT_KIND_CHECK = "kind IN ('llm_call', 'tool_call', 'resolver', 'response')"


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
        CheckConstraint(_AUDIT_KIND_CHECK, name="ck_audit_log_kind"),
    )
