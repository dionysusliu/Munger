"""communities.search_vector generated tsvector + GIN for ranked thematic search (SP3.3).

A GENERATED ALWAYS ... STORED column keeps itself in sync on every report write —
no trigger, no service-side maintenance.

Revision ID: 014_community_search_vector
Revises: 013_message_feedback
Create Date: 2026-06-11
"""

from alembic import op

revision = "014_community_search_vector"
down_revision = "013_message_feedback"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE communities ADD COLUMN search_vector tsvector
        GENERATED ALWAYS AS (
            to_tsvector('english',
                coalesce(title, '') || ' ' || coalesce(summary, '') || ' ' || coalesce(keywords, ''))
        ) STORED
    """)
    op.execute("CREATE INDEX ix_communities_search_vector ON communities USING gin (search_vector)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_communities_search_vector")
    op.execute("ALTER TABLE communities DROP COLUMN IF EXISTS search_vector")
