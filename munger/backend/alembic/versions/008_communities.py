"""communities table + entities.community_id.

Revision ID: 008_communities
Revises: 007_entity_edges_and_salience
Create Date: 2026-06-10
"""

from alembic import op
import sqlalchemy as sa

revision = "008_communities"
down_revision = "007_entity_edges_and_salience"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "communities",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("level", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.add_column(
        "entities",
        sa.Column("community_id", sa.Integer(), sa.ForeignKey("communities.id", ondelete="SET NULL"), nullable=True),
    )
    op.create_index("ix_entities_community_id", "entities", ["community_id"])


def downgrade() -> None:
    op.drop_index("ix_entities_community_id", table_name="entities")
    op.drop_column("entities", "community_id")
    op.drop_table("communities")
