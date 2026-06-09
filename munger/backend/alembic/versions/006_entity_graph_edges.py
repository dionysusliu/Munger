"""Materialized view for entity graph edges.

Revision ID: 006_entity_graph_edges
Revises: 005_chunk_map_status
Create Date: 2026-06-09
"""

from alembic import op

revision = "006_entity_graph_edges"
down_revision = "005_chunk_map_status"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE MATERIALIZED VIEW IF NOT EXISTS entity_graph_edges AS
        SELECT
            er.id,
            er.source_entity_id,
            er.target_entity_id,
            er.relationship_type,
            er.method,
            er.confidence,
            er.source_id,
            er.chunk_id,
            se.name AS source_entity_name,
            te.name AS target_entity_name
        FROM entity_relationships er
        JOIN entities se ON se.id = er.source_entity_id
        JOIN entities te ON te.id = er.target_entity_id
        WITH NO DATA
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS ix_entity_graph_edges_id
        ON entity_graph_edges (id)
        """
    )


def downgrade() -> None:
    op.execute("DROP MATERIALIZED VIEW IF EXISTS entity_graph_edges")
