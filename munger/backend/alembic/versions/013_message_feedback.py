"""chat_messages rating + feedback_note (SP4.2).

Revision ID: 013_message_feedback
Revises: 012_chat
Create Date: 2026-06-10
"""

import sqlalchemy as sa
from alembic import op

revision = "013_message_feedback"
down_revision = "012_chat"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("chat_messages", sa.Column("rating", sa.Integer, nullable=True))
    op.add_column("chat_messages", sa.Column("feedback_note", sa.Text, nullable=True))


def downgrade() -> None:
    op.drop_column("chat_messages", "feedback_note")
    op.drop_column("chat_messages", "rating")
