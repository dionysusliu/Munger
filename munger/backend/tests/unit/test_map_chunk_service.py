"""Unit tests for parallel MAP chunk workers."""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock

from sqlalchemy import select

from app.core.database import async_session_maker
from app.models.chunk import Chunk
from app.models.chunk_extraction import ChunkExtraction
from app.models.source import Source
from app.schemas.extraction import ExtractionResult, GleanResult
from app.services.chunk_service import ChunkService
from app.services.map_chunk_service import MapChunkService
from tests.conftest import run_async


def _mock_settings():
    settings = MagicMock()
    settings.ingest_chunk_worker_concurrency = 5
    settings.ingest_max_gleanings = 1
    settings.embedding_model = "test-embed"
    settings.ingest_extraction_window_chunks = 1
    return settings


class TestMapChunkServiceConcurrency:
    def test_max_observed_concurrency_under_semaphore(self):
        mock_settings = _mock_settings()
        active = 0
        max_active = 0
        lock = asyncio.Lock()

        async def slow_prefix(*_args, **_kwargs):
            nonlocal active, max_active
            async with lock:
                active += 1
                max_active = max(max_active, active)
            await asyncio.sleep(0.05)
            async with lock:
                active -= 1
            return "ctx"

        async def slow_chat(messages, **kwargs):
            if "YES or NO" in str(messages):
                return "NO"
            return '{"entities":[],"relationships":[]}'

        llm = AsyncMock()
        llm.chat = slow_chat
        llm.embed_texts = AsyncMock(return_value=[[0.1] * 768] * 10)

        chunk_svc = ChunkService(llm_service=llm, settings=mock_settings)
        chunk_svc._contextual_prefix = slow_prefix  # type: ignore[method-assign]

        service = MapChunkService(llm_service=llm, chunk_service=chunk_svc, settings=mock_settings)

        async def _run():
            async with async_session_maker() as session:
                source = Source(
                    title="Concurrency Test",
                    filename="c.txt",
                    file_path="sources/c.txt",
                    file_type="txt",
                    content_hash="hash-c",
                    file_size=100,
                    content_text="word " * 200,
                    status="chunking",
                )
                session.add(source)
                await session.commit()
                await session.refresh(source)

                for i in range(10):
                    session.add(
                        Chunk(
                            source_id=source.id,
                            chunk_index=i,
                            content=f"chunk {i} content",
                            token_count=10,
                            doc_char_start=i * 10,
                            doc_char_end=(i + 1) * 10,
                        )
                    )
                await session.commit()
                return source.id

        source_id = run_async(_run())
        stats = run_async(service.map_chunks(source_id))
        assert stats["chunks_processed"] == 10
        assert stats["max_observed_concurrency"] >= 2
        assert stats["max_observed_concurrency"] <= mock_settings.ingest_chunk_worker_concurrency


class TestMapChunkServiceGlean:
    def test_glean_round_1_only_on_yes(self):
        mock_settings = _mock_settings()

        async def gated_chat(messages, **kwargs):
            content = str(messages)
            if "YES or NO" in content:
                return "YES"
            if "missed" in content.lower():
                return (
                    '{"missed_entities":[{"name":"Extra","type":"concept",'
                    '"description":"missed one","char_start":0,"char_end":5}],'
                    '"missed_relationships":[],"reasoning":"found more"}'
                )
            return (
                '{"entities":[{"name":"Alpha","type":"concept","description":"first",'
                '"char_start":0,"char_end":5}],"relationships":[]}'
            )

        llm = AsyncMock()
        llm.chat = gated_chat

        async def chat_structured(messages, response_model, **kwargs):
            raw = await gated_chat(messages, **kwargs)
            data = json.loads(raw)
            return response_model.model_validate(data)

        llm.chat_structured = chat_structured
        llm.embed_texts = AsyncMock(return_value=[[0.2] * 768])

        chunk_svc = ChunkService(llm_service=llm, settings=mock_settings)
        chunk_svc._contextual_prefix = AsyncMock(return_value="prefix")  # type: ignore[method-assign]
        service = MapChunkService(llm_service=llm, chunk_service=chunk_svc, settings=mock_settings)

        async def _setup():
            async with async_session_maker() as session:
                source = Source(
                    title="Glean Test",
                    filename="g.txt",
                    file_path="sources/g.txt",
                    file_type="txt",
                    content_hash="hash-g",
                    file_size=50,
                    content_text="Alpha beta gamma",
                    status="chunking",
                )
                session.add(source)
                await session.commit()
                await session.refresh(source)
                chunk = Chunk(
                    source_id=source.id,
                    chunk_index=0,
                    content="Alpha beta",
                    token_count=5,
                    doc_char_start=0,
                    doc_char_end=10,
                )
                session.add(chunk)
                await session.commit()
                await session.refresh(chunk)
                return source.id, chunk.id

        source_id, chunk_id = run_async(_setup())
        stats = run_async(service.map_chunks(source_id))
        assert stats["glean_entities_added"] == 1

        async def _check():
            async with async_session_maker() as session:
                extractions = (
                    await session.execute(
                        select(ChunkExtraction).where(ChunkExtraction.chunk_id == chunk_id)
                    )
                ).scalars().all()
                rounds = {e.glean_round for e in extractions}
                assert 0 in rounds
                assert 1 in rounds

        run_async(_check())
