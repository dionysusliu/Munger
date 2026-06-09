"""Cross-chunk linking columns and indexes.

Revision ID: 004_cross_chunk_linking
Revises: 003_provenance
Create Date: 2026-06-09
"""

from alembic import op
from sqlalchemy import text

revision = "004_cross_chunk_linking"
down_revision = "003_provenance"
branch_labels = None
depends_on = None


def _require_pgvector() -> None:
    conn = op.get_bind()
    row = conn.execute(
        text("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
    ).fetchone()
    if row is None:
        raise RuntimeError("pgvector extension is required before migration 004")


def upgrade() -> None:
    _require_pgvector()
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    op.execute(
        """
        ALTER TABLE entity_relationships
            ADD COLUMN IF NOT EXISTS confidence DOUBLE PRECISION,
            ADD COLUMN IF NOT EXISTS method VARCHAR(20)
        """
    )
    op.execute(
        """
        ALTER TABLE entity_mentions
            ADD COLUMN IF NOT EXISTS mention_method VARCHAR(20) DEFAULT 'extract'
        """
    )
    op.execute(
        """
        ALTER TABLE chunks
            ADD COLUMN IF NOT EXISTS content_uri VARCHAR(512)
        """
    )

    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_entities_name_trgm
        ON entities USING gin (name gin_trgm_ops)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_entities_embedding_hnsw
        ON entities USING hnsw (embedding vector_cosine_ops)
        """
    )

    # Collapse duplicate mentions per entity+chunk before enforcing uniqueness.
    op.execute(
        """
        DELETE FROM entity_mentions em
        USING entity_mentions em2
        WHERE em.id > em2.id
          AND em.entity_id = em2.entity_id
          AND em.chunk_id IS NOT NULL
          AND em.chunk_id = em2.chunk_id
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_entity_mentions_entity_chunk
        ON entity_mentions (entity_id, chunk_id)
        WHERE chunk_id IS NOT NULL
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_entity_mentions_entity_chunk")
    op.execute("DROP INDEX IF EXISTS ix_entities_embedding_hnsw")
    op.execute("DROP INDEX IF EXISTS ix_entities_name_trgm")
    op.execute("ALTER TABLE chunks DROP COLUMN IF EXISTS content_uri")
    op.execute("ALTER TABLE entity_mentions DROP COLUMN IF EXISTS mention_method")
    op.execute(
        "ALTER TABLE entity_relationships DROP COLUMN IF EXISTS confidence, "
        "DROP COLUMN IF EXISTS method"
    )
