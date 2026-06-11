"""Index audit: add hot-path + FK indexes; drop the legacy entity_graph_edges matview.

Grounded in the actual queries this codebase runs:
- update_for_source / reduce filter entity_relationships, entity_mentions,
  chunk_extractions by source_id (were seq scans — FK columns are not auto-indexed).
- create_link / link_wiki_pages look up wiki_links by (from_page_id, to_page_id)
  (table had only a PK) — added as UNIQUE since create_link assumes one row per pair.
- hash_dedup filters sources by content_hash (sources had only a PK).
- find_or_create / resolution match entities by lower(name)+entity_type (the raw-name
  index can't serve lower()).
- target_entity_id / chunk_id / wiki_page_id FK indexes support CASCADE deletes
  (entity merges in SP2.2).

Deferred (touches model-declared indexes → separate cleanup): trimming the
append-heavy ingest_events indexes (drop event_type, consolidate to (source_id, created_at)).

NOTE for production: create these CONCURRENTLY on a live box (plain CREATE here for dev).
If existing wiki_links data has duplicate (from,to) pairs, dedup before applying the unique.

Revision ID: 009_index_audit
Revises: 008_communities
Create Date: 2026-06-10
"""

from alembic import op

revision = "009_index_audit"
down_revision = "008_communities"
branch_labels = None
depends_on = None

_LEGACY_MATVIEW = """
    CREATE MATERIALIZED VIEW IF NOT EXISTS entity_graph_edges AS
    SELECT er.id, er.source_entity_id, er.target_entity_id, er.relationship_type,
           er.method, er.confidence, er.source_id, er.chunk_id,
           se.name AS source_entity_name, te.name AS target_entity_name
    FROM entity_relationships er
    JOIN entities se ON se.id = er.source_entity_id
    JOIN entities te ON te.id = er.target_entity_id
    WITH NO DATA
"""


def upgrade() -> None:
    op.create_unique_constraint("uq_wiki_links_pair", "wiki_links", ["from_page_id", "to_page_id"])
    op.create_index("ix_entity_relationships_source_id", "entity_relationships", ["source_id"])
    op.create_index("ix_entity_relationships_target_entity_id", "entity_relationships", ["target_entity_id"])
    op.create_index("ix_entity_mentions_source_id", "entity_mentions", ["source_id"])
    op.create_index("ix_entity_mentions_chunk_id", "entity_mentions", ["chunk_id"])
    op.create_index("ix_entity_mentions_wiki_page_id", "entity_mentions", ["wiki_page_id"])
    op.create_index("ix_chunk_extractions_source_id", "chunk_extractions", ["source_id"])
    op.create_index("ix_sources_content_hash", "sources", ["content_hash"])
    op.create_index("ix_wiki_pages_source_id", "wiki_pages", ["source_id"])
    op.execute("CREATE INDEX ix_entities_lower_name_type ON entities (lower(name), entity_type)")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS entity_graph_edges")


def downgrade() -> None:
    op.execute(_LEGACY_MATVIEW)
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_entity_graph_edges_id ON entity_graph_edges (id)")
    op.execute("DROP INDEX IF EXISTS ix_entities_lower_name_type")
    op.drop_index("ix_wiki_pages_source_id", table_name="wiki_pages")
    op.drop_index("ix_sources_content_hash", table_name="sources")
    op.drop_index("ix_chunk_extractions_source_id", table_name="chunk_extractions")
    op.drop_index("ix_entity_mentions_wiki_page_id", table_name="entity_mentions")
    op.drop_index("ix_entity_mentions_chunk_id", table_name="entity_mentions")
    op.drop_index("ix_entity_mentions_source_id", table_name="entity_mentions")
    op.drop_index("ix_entity_relationships_target_entity_id", table_name="entity_relationships")
    op.drop_index("ix_entity_relationships_source_id", table_name="entity_relationships")
    op.drop_constraint("uq_wiki_links_pair", "wiki_links", type_="unique")
