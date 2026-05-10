"""extend audit_log.kind to allow 'resolver'

Adds ``'resolver'`` to the kind CHECK constraint. ``'verifier'`` is kept
so historical rows persisted under the old offset-verification design
remain valid; live writes only emit ``'resolver'`` going forward.

SQLite has no ALTER TABLE for CHECK constraints — Alembic's
``batch_alter_table`` recreates the table behind the scenes. The
``cost_log`` view depends on ``audit_log`` and blocks the rename, so we
drop it before the batch and recreate it after.

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-10
"""

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


_NEW_CHECK = "kind IN ('llm_call', 'tool_call', 'resolver', 'verifier', 'response')"
_OLD_CHECK = "kind IN ('llm_call', 'tool_call', 'verifier', 'response')"

_RECREATE_VIEW = """
CREATE VIEW cost_log AS
SELECT step_id, question_id, conversation_id, timestamp, payload, usage
FROM audit_log
WHERE kind = 'llm_call'
"""


def upgrade() -> None:
    op.execute("DROP VIEW IF EXISTS cost_log")
    with op.batch_alter_table("audit_log") as batch_op:
        batch_op.drop_constraint("ck_audit_log_kind", type_="check")
        batch_op.create_check_constraint("ck_audit_log_kind", _NEW_CHECK)
    op.execute(_RECREATE_VIEW)


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS cost_log")
    with op.batch_alter_table("audit_log") as batch_op:
        batch_op.drop_constraint("ck_audit_log_kind", type_="check")
        batch_op.create_check_constraint("ck_audit_log_kind", _OLD_CHECK)
    op.execute(_RECREATE_VIEW)
