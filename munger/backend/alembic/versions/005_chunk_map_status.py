"""Per-chunk map status for selective re-map on ingest retry.

Revision ID: 005_chunk_map_status
Revises: 004_cross_chunk_linking
Create Date: 2026-06-09
"""

from alembic import op

revision = "005_chunk_map_status"
down_revision = "004_cross_chunk_linking"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE chunks
            ADD COLUMN IF NOT EXISTS map_status VARCHAR(20) NOT NULL DEFAULT 'pending',
            ADD COLUMN IF NOT EXISTS map_attempts INT NOT NULL DEFAULT 0,
            ADD COLUMN IF NOT EXISTS map_last_error TEXT,
            ADD COLUMN IF NOT EXISTS mapped_at TIMESTAMPTZ,
            ADD COLUMN IF NOT EXISTS map_started_at TIMESTAMPTZ
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_chunks_source_map_status
        ON chunks (source_id, map_status)
        """
    )
    op.execute(
        """
        UPDATE chunks c
        SET map_status = 'done', mapped_at = NOW()
        WHERE EXISTS (
            SELECT 1 FROM chunk_extractions ce
            WHERE ce.chunk_id = c.id AND ce.glean_round = 0
        )
        AND c.embedding IS NOT NULL
        """
    )
    op.execute(
        """
        ALTER TABLE sources
            ADD COLUMN IF NOT EXISTS chunked_content_hash VARCHAR(64)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_chunks_source_map_status")
    op.execute("ALTER TABLE sources DROP COLUMN IF EXISTS chunked_content_hash")
    op.execute(
        """
        ALTER TABLE chunks
            DROP COLUMN IF EXISTS map_started_at,
            DROP COLUMN IF EXISTS mapped_at,
            DROP COLUMN IF EXISTS map_last_error,
            DROP COLUMN IF EXISTS map_attempts,
            DROP COLUMN IF EXISTS map_status
        """
    )
