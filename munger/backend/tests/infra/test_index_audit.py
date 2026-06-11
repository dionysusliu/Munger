"""Migration 009: the hot-path / FK indexes exist; the legacy matview is gone."""

from sqlalchemy import text

from app.core.database import async_session_maker
from tests.conftest import run_async

EXPECTED_INDEXES = {
    "uq_wiki_links_pair",
    "ix_entity_relationships_source_id",
    "ix_entity_relationships_target_entity_id",
    "ix_entity_mentions_source_id",
    "ix_entity_mentions_chunk_id",
    "ix_entity_mentions_wiki_page_id",
    "ix_chunk_extractions_source_id",
    "ix_sources_content_hash",
    "ix_wiki_pages_source_id",
    "ix_entities_lower_name_type",
}


def test_audit_indexes_present_and_legacy_matview_dropped():
    async def _inner():
        async with async_session_maker() as session:
            idx = {
                r[0]
                for r in (
                    await session.execute(
                        text("SELECT indexname FROM pg_indexes WHERE schemaname='public'")
                    )
                ).all()
            }
            mviews = {
                r[0]
                for r in (
                    await session.execute(
                        text("SELECT matviewname FROM pg_matviews WHERE schemaname='public'")
                    )
                ).all()
            }
            return idx, mviews

    idx, mviews = run_async(_inner())
    missing = EXPECTED_INDEXES - idx
    assert not missing, f"migration 009 did not create: {missing}"
    assert "entity_graph_edges" not in mviews, "legacy entity_graph_edges matview should be dropped"
