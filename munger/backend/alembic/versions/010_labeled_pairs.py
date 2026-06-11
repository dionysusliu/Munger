"""labeled_pairs: human match/reject decisions for entity resolution (SP2.2).

Revision ID: 010_labeled_pairs
Revises: 009_index_audit
Create Date: 2026-06-10
"""

import sqlalchemy as sa
from alembic import op

revision = "010_labeled_pairs"
down_revision = "009_index_audit"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "labeled_pairs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("entity_a_id", sa.Integer, sa.ForeignKey("entities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("entity_b_id", sa.Integer, sa.ForeignKey("entities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("label", sa.String(10), nullable=False),
        sa.Column("note", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("entity_a_id < entity_b_id", name="ck_labeled_pairs_ordered"),
        sa.UniqueConstraint("entity_a_id", "entity_b_id", name="uq_labeled_pairs_pair"),
    )


def downgrade() -> None:
    op.drop_table("labeled_pairs")
