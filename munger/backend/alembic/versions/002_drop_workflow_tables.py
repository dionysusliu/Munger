"""Drop legacy workflow execution tables.

Revision ID: 002_drop_workflow
Revises: 001_initial
Create Date: 2026-06-09
"""

from alembic import op

revision = "002_drop_workflow"
down_revision = "001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Tables may be absent on fresh installs where 001 no longer creates them.
    op.execute("DROP TABLE IF EXISTS workflow_run_steps CASCADE")
    op.execute("DROP TABLE IF EXISTS workflow_runs CASCADE")
    op.execute("DROP TABLE IF EXISTS workflows CASCADE")


def downgrade() -> None:
    # Irreversible: Workflow ORM models removed from codebase.
    pass
