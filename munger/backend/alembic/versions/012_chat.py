"""chat_sessions + chat_messages (SP4.1).

Revision ID: 012_chat
Revises: 011_community_reports
Create Date: 2026-06-10
"""

import sqlalchemy as sa
from alembic import op

revision = "012_chat"
down_revision = "011_community_reports"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "chat_sessions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("title", sa.String(200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "chat_messages",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("session_id", sa.Integer, sa.ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("citations", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_chat_messages_session_id", "chat_messages", ["session_id"])


def downgrade() -> None:
    op.drop_index("ix_chat_messages_session_id", table_name="chat_messages")
    op.drop_table("chat_messages")
    op.drop_table("chat_sessions")
