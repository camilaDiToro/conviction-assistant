"""initial schema: passages, audit_log, cost_log

Revision ID: 0001
Revises:
Create Date: 2026-05-09
"""

import sqlalchemy as sa

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "passages",
        sa.Column("id", sa.Text, primary_key=True),
        sa.Column("document_id", sa.Text, nullable=False),
        sa.Column("document_title", sa.Text, nullable=False),
        sa.Column("heading", sa.Text, nullable=False),
        sa.Column("heading_path", sa.Text, nullable=False),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("document_updated", sa.Text, nullable=True),
        sa.Column("ordinal", sa.Integer, nullable=False),
    )
    op.create_index(
        "ix_passages_doc",
        "passages",
        ["document_id", "ordinal"],
    )

    op.create_table(
        "audit_log",
        sa.Column("step_id", sa.Text, primary_key=True),
        sa.Column("question_id", sa.Text, nullable=False),
        sa.Column("conversation_id", sa.Text, nullable=False),
        sa.Column("timestamp", sa.Text, nullable=False),
        sa.Column("kind", sa.Text, nullable=False),
        sa.Column("payload", sa.Text, nullable=False),
        sa.Column("usage", sa.Text, nullable=True),
        sa.CheckConstraint(
            "kind IN ('llm_call', 'tool_call', 'verifier', 'response')",
            name="ck_audit_log_kind",
        ),
    )
    op.create_index("ix_audit_question", "audit_log", ["question_id"])
    op.create_index("ix_audit_conversation", "audit_log", ["conversation_id"])

    op.execute(
        """
        CREATE VIEW cost_log AS
        SELECT step_id, question_id, conversation_id, timestamp, payload, usage
        FROM audit_log
        WHERE kind = 'llm_call'
        """
    )


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS cost_log")
    op.drop_index("ix_audit_conversation", table_name="audit_log")
    op.drop_index("ix_audit_question", table_name="audit_log")
    op.drop_table("audit_log")
    op.drop_index("ix_passages_doc", table_name="passages")
    op.drop_table("passages")
