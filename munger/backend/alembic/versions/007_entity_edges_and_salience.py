"""entity_edges derived adjacency + entities.salience/canonical_entity_id.

Revision ID: 007_entity_edges_and_salience
Revises: 006_entity_graph_edges
Create Date: 2026-06-10
"""

from alembic import op
import sqlalchemy as sa

revision = "007_entity_edges_and_salience"
down_revision = "006_entity_graph_edges"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("entities", sa.Column("salience", sa.Double(), nullable=False, server_default="0"))
    op.add_column(
        "entities",
        sa.Column("canonical_entity_id", sa.Integer(), sa.ForeignKey("entities.id", ondelete="SET NULL"), nullable=True),
    )
    op.create_index("ix_entities_canonical_entity_id", "entities", ["canonical_entity_id"])

    op.create_table(
        "entity_edges",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("src_entity_id", sa.Integer(), sa.ForeignKey("entities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tgt_entity_id", sa.Integer(), sa.ForeignKey("entities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("weight", sa.Double(), nullable=False, server_default="0"),
        sa.Column("evidence_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("top_rel_type", sa.String(length=50), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("src_entity_id", "tgt_entity_id", name="uq_entity_edges_pair"),
        sa.CheckConstraint("src_entity_id < tgt_entity_id", name="ck_entity_edges_ordered"),
    )
    op.execute("CREATE INDEX ix_entity_edges_src_weight ON entity_edges (src_entity_id, weight DESC)")
    op.execute("CREATE INDEX ix_entity_edges_tgt_weight ON entity_edges (tgt_entity_id, weight DESC)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_entity_edges_tgt_weight")
    op.execute("DROP INDEX IF EXISTS ix_entity_edges_src_weight")
    op.drop_table("entity_edges")
    op.drop_index("ix_entities_canonical_entity_id", table_name="entities")
    op.drop_column("entities", "canonical_entity_id")
    op.drop_column("entities", "salience")
