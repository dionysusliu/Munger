"""Integration-style tests for selective chunk re-map."""

import asyncio

from sqlalchemy import select

from app.core.database import async_session_maker
from app.models.chunk import Chunk
from app.models.source import Source
from app.services.chunk_map_status import MAP_DONE, MAP_PENDING, chunks_needing_map


def test_selective_remap_skips_done_chunks():
    async def _run():
        async with async_session_maker() as session:
            source = Source(
                title="Retry Test",
                filename="r.txt",
                file_path="sources/r.txt",
                file_type="txt",
                content_hash="hash-retry",
                chunked_content_hash="hash-retry",
                file_size=10,
                content_text="one two three",
                status="extracting",
            )
            session.add(source)
            await session.commit()
            await session.refresh(source)

            done = Chunk(
                source_id=source.id,
                chunk_index=0,
                content="one",
                token_count=1,
                doc_char_start=0,
                doc_char_end=3,
                map_status=MAP_DONE,
            )
            pending = Chunk(
                source_id=source.id,
                chunk_index=1,
                content="two",
                token_count=1,
                doc_char_start=4,
                doc_char_end=7,
                map_status=MAP_PENDING,
            )
            session.add_all([done, pending])
            await session.commit()

            needing = await chunks_needing_map(source.id)
            assert needing == [pending.id]

    asyncio.run(_run())
