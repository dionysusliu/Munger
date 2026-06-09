"""Unit tests for REDUCE Prof description merge."""

from unittest.mock import AsyncMock, MagicMock

from sqlalchemy import select

from app.core.database import async_session_maker
from app.models.chunk import Chunk
from app.models.chunk_extraction import ChunkExtraction
from app.models.entity import Entity
from app.models.source import Source
from app.services.resolution_service import ResolutionService
from tests.conftest import run_async


def _mock_settings():
    settings = MagicMock()
    settings.ingest_chunk_worker_concurrency = 5
    return settings


class TestReduceProfMerge:
    def test_merges_multiple_descriptions_within_source(self):
        mock_settings = _mock_settings()
        llm = AsyncMock()
        llm.chat = AsyncMock(return_value="Merged description from both sources")
        service = ResolutionService(llm_service=llm, settings=mock_settings)

        async def _setup():
            async with async_session_maker() as session:
                source = Source(
                    title="Prof Test",
                    filename="p.txt",
                    file_path="sources/p.txt",
                    file_type="txt",
                    content_hash="hash-p",
                    file_size=50,
                    content_text="Alice and Bob discussed physics.",
                    status="extracting",
                )
                session.add(source)
                await session.commit()
                await session.refresh(source)

                chunk = Chunk(
                    source_id=source.id,
                    chunk_index=0,
                    content="Alice physics",
                    token_count=5,
                    doc_char_start=0,
                    doc_char_end=20,
                )
                session.add(chunk)
                await session.commit()
                await session.refresh(chunk)

                session.add(
                    ChunkExtraction(
                        chunk_id=chunk.id,
                        source_id=source.id,
                        glean_round=0,
                        entities=[
                            {"name": "Alice", "type": "person", "description": "Physicist A"},
                            {"name": "Alice", "type": "person", "description": "Researcher on QM"},
                        ],
                        relationships=[],
                    )
                )
                await session.commit()
                return source.id

        source_id = run_async(_setup())
        stats = run_async(service.reduce_entities(source_id))
        assert stats["prof_merges"] == 1
        assert stats["entities_canonical"] == 1
        assert llm.chat.await_count >= 1

        async def _check():
            async with async_session_maker() as session:
                entity = (
                    await session.execute(select(Entity).where(Entity.name == "Alice"))
                ).scalar_one()
                assert entity.description == "Merged description from both sources"

        run_async(_check())

    def test_reconciles_with_existing_global_description(self):
        mock_settings = _mock_settings()
        llm = AsyncMock()
        llm.chat = AsyncMock(return_value="Reconciled global description")
        service = ResolutionService(llm_service=llm, settings=mock_settings)

        async def _setup():
            async with async_session_maker() as session:
                source = Source(
                    title="Reconcile Test",
                    filename="r.txt",
                    file_path="sources/r.txt",
                    file_type="txt",
                    content_hash="hash-r",
                    file_size=50,
                    content_text="Bob works here.",
                    status="extracting",
                )
                session.add(source)
                await session.commit()
                await session.refresh(source)

                existing = Entity(
                    name="Bob",
                    entity_type="person",
                    description="Existing global bio",
                    mention_count=2,
                )
                session.add(existing)

                chunk = Chunk(
                    source_id=source.id,
                    chunk_index=0,
                    content="Bob works",
                    token_count=3,
                    doc_char_start=0,
                    doc_char_end=10,
                )
                session.add(chunk)
                await session.commit()
                await session.refresh(chunk)

                session.add(
                    ChunkExtraction(
                        chunk_id=chunk.id,
                        source_id=source.id,
                        glean_round=0,
                        entities=[{"name": "Bob", "type": "person", "description": "New source bio"}],
                        relationships=[],
                    )
                )
                await session.commit()
                return source.id

        source_id = run_async(_setup())
        run_async(service.reduce_entities(source_id))

        async def _check():
            async with async_session_maker() as session:
                entity = (
                    await session.execute(select(Entity).where(Entity.name == "Bob"))
                ).scalar_one()
                assert entity.description == "Reconciled global description"

        run_async(_check())
