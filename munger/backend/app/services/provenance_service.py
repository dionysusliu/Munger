"""Provenance chain queries: entity → mention → chunk → source."""

from __future__ import annotations

from sqlalchemy import select

from app.core.database import async_session_maker
from app.models.chunk import Chunk
from app.models.entity import EntityMention
from app.models.source import Source


class ProvenanceService:
    async def get_provenance_chain(self, entity_id: int) -> list[dict]:
        async with async_session_maker() as session:
            rows = await session.execute(
                select(EntityMention, Source, Chunk)
                .outerjoin(Source, Source.id == EntityMention.source_id)
                .outerjoin(Chunk, Chunk.id == EntityMention.chunk_id)
                .where(EntityMention.entity_id == entity_id)
                .order_by(EntityMention.created_at.desc())
            )

            chain: list[dict] = []
            for mention, source, chunk in rows.all():
                excerpt = mention.context or ""
                if source and mention.char_start is not None and mention.char_end is not None:
                    text = source.content_text or ""
                    excerpt = text[mention.char_start : mention.char_end]
                elif chunk and chunk.content:
                    excerpt = chunk.content[:500]

                chain.append(
                    {
                        "mention_id": mention.id,
                        "source_id": mention.source_id,
                        "source_title": source.title if source else None,
                        "chunk_id": mention.chunk_id,
                        "char_start": mention.char_start,
                        "char_end": mention.char_end,
                        "excerpt": excerpt,
                    }
                )
            return chain
