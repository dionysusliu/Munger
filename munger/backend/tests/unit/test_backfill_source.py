"""Regression tests for backfill source cleanup."""

from sqlalchemy import select

from app.core.database import async_session_maker
from app.models.chunk import Chunk
from app.models.chunk_extraction import ChunkExtraction
from app.models.entity import EntityMention
from app.models.entity_relationship import EntityRelationship
from app.models.source import Source


class TestBackfillSourceCleanup:
    def test_backfill_deletes_chunks_extractions_mentions_and_relationships(
        self, client, create_source, create_entity
    ):
        source = create_source(content_text="Backfill test content for cleanup.")
        entity = create_entity(name="Rel Entity", entity_type="concept")

        async def _seed():
            async with async_session_maker() as session:
                chunk = Chunk(
                    source_id=source.id,
                    chunk_index=0,
                    content="chunk",
                    token_count=1,
                    doc_char_start=0,
                    doc_char_end=5,
                )
                session.add(chunk)
                await session.flush()
                session.add(
                    ChunkExtraction(
                        chunk_id=chunk.id,
                        source_id=source.id,
                        glean_round=0,
                        entities=[],
                        relationships=[],
                    )
                )
                session.add(
                    EntityMention(
                        entity_id=entity.id,
                        source_id=source.id,
                        chunk_id=chunk.id,
                        context="ctx",
                    )
                )
                session.add(
                    EntityRelationship(
                        source_entity_id=entity.id,
                        target_entity_id=entity.id,
                        relationship_type="relates_to",
                        source_id=source.id,
                        chunk_id=chunk.id,
                    )
                )
                await session.commit()

        from tests.conftest import run_async

        run_async(_seed())

        response = client.post(f"/api/sources/{source.id}/backfill")
        assert response.status_code in (200, 202)

        async def _assert_clean():
            async with async_session_maker() as session:
                chunks = (
                    await session.execute(select(Chunk).where(Chunk.source_id == source.id))
                ).scalars().all()
                extractions = (
                    await session.execute(
                        select(ChunkExtraction).where(ChunkExtraction.source_id == source.id)
                    )
                ).scalars().all()
                mentions = (
                    await session.execute(
                        select(EntityMention).where(EntityMention.source_id == source.id)
                    )
                ).scalars().all()
                relationships = (
                    await session.execute(
                        select(EntityRelationship).where(EntityRelationship.source_id == source.id)
                    )
                ).scalars().all()
                assert len(chunks) == 0
                assert len(extractions) == 0
                assert len(mentions) == 0
                assert len(relationships) == 0

        run_async(_assert_clean())
