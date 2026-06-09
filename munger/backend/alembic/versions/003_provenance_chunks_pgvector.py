"""Provenance chunks, pgvector, entity relationships.

Revision ID: 003_provenance
Revises: 002_drop_workflow
Create Date: 2026-06-08
"""

from alembic import op
from sqlalchemy import text

revision = "003_provenance"
down_revision = "002_drop_workflow"
branch_labels = None
depends_on = None

EMBED_DIM = 768


def _require_pgvector() -> None:
    conn = op.get_bind()
    row = conn.execute(
        text("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
    ).fetchone()
    if row is None:
        raise RuntimeError(
            "pgvector extension is not installed. Run scripts/bootstrap_postgres.py "
            "(or CREATE EXTENSION vector as superuser on this database) before alembic upgrade."
        )


def upgrade() -> None:
    _require_pgvector()

    op.execute(
        f"""
        CREATE TABLE chunks (
            id SERIAL PRIMARY KEY,
            source_id INTEGER NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
            chunk_index INTEGER NOT NULL,
            content TEXT NOT NULL,
            contextual_prefix TEXT,
            token_count INTEGER NOT NULL,
            doc_char_start INTEGER NOT NULL,
            doc_char_end INTEGER NOT NULL,
            embedding vector({EMBED_DIM}),
            embedding_model VARCHAR(100),
            created_at TIMESTAMPTZ DEFAULT now(),
            UNIQUE (source_id, chunk_index)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE chunk_extractions (
            id SERIAL PRIMARY KEY,
            chunk_id INTEGER NOT NULL REFERENCES chunks(id) ON DELETE CASCADE,
            source_id INTEGER NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
            entities JSONB NOT NULL DEFAULT '[]',
            relationships JSONB NOT NULL DEFAULT '[]',
            glean_round INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMPTZ DEFAULT now(),
            UNIQUE (chunk_id, glean_round)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE entity_relationships (
            id SERIAL PRIMARY KEY,
            source_entity_id INTEGER NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
            target_entity_id INTEGER NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
            relationship_type VARCHAR(50) NOT NULL,
            description TEXT,
            source_id INTEGER REFERENCES sources(id) ON DELETE CASCADE,
            chunk_id INTEGER REFERENCES chunks(id) ON DELETE SET NULL,
            created_at TIMESTAMPTZ DEFAULT now(),
            CONSTRAINT uq_entity_relationships_quad
                UNIQUE (source_entity_id, target_entity_id, relationship_type, source_id)
        )
        """
    )
    op.execute(
        """
        ALTER TABLE entity_mentions
            ADD COLUMN chunk_id INTEGER REFERENCES chunks(id) ON DELETE SET NULL,
            ADD COLUMN char_start INTEGER,
            ADD COLUMN char_end INTEGER
        """
    )
    op.execute(f"ALTER TABLE entities ADD COLUMN embedding vector({EMBED_DIM})")
    op.execute(
        """
        ALTER TABLE wiki_pages
            ADD COLUMN search_vector tsvector
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_wiki_pages_search_vector ON wiki_pages USING GIN (search_vector)"
    )
    op.execute(
        f"""
        CREATE INDEX IF NOT EXISTS ix_chunks_embedding_hnsw
        ON chunks USING hnsw (embedding vector_cosine_ops)
        """
    )
    op.execute(
        "ALTER TABLE ingest_jobs ADD COLUMN IF NOT EXISTS skill_name VARCHAR(50) NOT NULL DEFAULT 'ingest'"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE ingest_jobs DROP COLUMN IF EXISTS skill_name")
    op.execute("DROP INDEX IF EXISTS ix_chunks_embedding_hnsw")
    op.execute("DROP INDEX IF EXISTS ix_wiki_pages_search_vector")
    op.execute("ALTER TABLE wiki_pages DROP COLUMN IF EXISTS search_vector")
    op.execute("ALTER TABLE entities DROP COLUMN IF EXISTS embedding")
    op.execute(
        """
        ALTER TABLE entity_mentions
            DROP COLUMN IF EXISTS char_end,
            DROP COLUMN IF EXISTS char_start,
            DROP COLUMN IF EXISTS chunk_id
        """
    )
    op.execute("DROP TABLE IF EXISTS entity_relationships CASCADE")
    op.execute("DROP TABLE IF EXISTS chunk_extractions CASCADE")
    op.execute("DROP TABLE IF EXISTS chunks CASCADE")
