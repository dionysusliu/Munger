"""Token-based chunking with contextual prefixes and embeddings."""

from __future__ import annotations

import logging
from dataclasses import dataclass

import tiktoken
from sqlalchemy import delete, select

from app.core.config import Settings, get_settings
from app.core.database import async_session_maker
from app.models.chunk import Chunk
from app.models.source import Source
from app.services.llm_service import LLMService
from app.services.vector_store import VectorStore, get_vector_store

logger = logging.getLogger(__name__)

CONTEXTUAL_PREFIX_PROMPT = (
    "Give a short succinct context to situate this chunk within the overall document "
    "for improving search retrieval. Answer only with the succinct context."
)


@dataclass
class ChunkSegment:
    content: str
    token_count: int
    doc_char_start: int
    doc_char_end: int


class ChunkService:
    def __init__(
        self,
        llm_service: LLMService | None,
        settings: Settings | None = None,
        vector_store: VectorStore | None = None,
    ):
        self.llm = llm_service
        self.settings = settings or get_settings()
        self.vectors = vector_store or get_vector_store(self.settings)

    def _encoding(self):
        try:
            return tiktoken.get_encoding("cl100k_base")
        except Exception:
            return tiktoken.get_encoding("gpt2")

    def split_text(
        self,
        text: str,
        *,
        chunk_size: int | None = None,
        overlap: int | None = None,
    ) -> list[ChunkSegment]:
        chunk_size = chunk_size or self.settings.ingest_chunk_size_tokens
        overlap = overlap or self.settings.ingest_chunk_overlap_tokens
        enc = self._encoding()
        tokens = enc.encode(text)
        if len(tokens) <= chunk_size:
            return [
                ChunkSegment(
                    content=text,
                    token_count=len(tokens),
                    doc_char_start=0,
                    doc_char_end=len(text),
                )
            ]

        segments: list[ChunkSegment] = []
        start = 0
        while start < len(tokens):
            end = min(start + chunk_size, len(tokens))
            chunk_tokens = tokens[start:end]
            chunk_text = enc.decode(chunk_tokens)
            char_start = len(enc.decode(tokens[:start]))
            char_end = len(enc.decode(tokens[:end]))
            segments.append(
                ChunkSegment(
                    content=chunk_text,
                    token_count=len(chunk_tokens),
                    doc_char_start=char_start,
                    doc_char_end=char_end,
                )
            )
            if end >= len(tokens):
                break
            start = end - overlap

        return segments

    async def _contextual_prefix(self, full_doc: str, chunk_text: str) -> str:
        if not self.llm:
            return ""
        try:
            messages = [
                {"role": "system", "content": CONTEXTUAL_PREFIX_PROMPT},
                {
                    "role": "user",
                    "content": f"<document>\n{full_doc[:12000]}\n</document>\n\n<chunk>\n{chunk_text}\n</chunk>",
                },
            ]
            return (await self.llm.chat(messages, max_tokens=150, temperature=0.0)).strip()
        except Exception as exc:
            logger.warning("Contextual prefix failed: %s", exc)
            return ""

    async def needs_resplit(self, source_id: int) -> bool:
        """True when source has no chunks or content_hash changed since last split."""
        async with async_session_maker() as session:
            source = await session.get(Source, source_id)
            if not source or not source.content_text:
                raise ValueError("No content_text to chunk")
            result = await session.execute(
                select(Chunk.id).where(Chunk.source_id == source_id).limit(1)
            )
            if result.scalar_one_or_none() is None:
                return True
            return source.chunked_content_hash != source.content_hash

    async def ensure_chunks(self, source_id: int) -> list[Chunk]:
        """Return existing chunks or split when missing / content hash changed."""
        if await self.needs_resplit(source_id):
            return await self.split_chunks(source_id)
        async with async_session_maker() as session:
            result = await session.execute(
                select(Chunk).where(Chunk.source_id == source_id).order_by(Chunk.chunk_index)
            )
            return list(result.scalars().all())

    async def split_chunks(self, source_id: int) -> list[Chunk]:
        """Split source text into chunks without contextual prefix or embeddings."""
        async with async_session_maker() as session:
            source = await session.get(Source, source_id)
            if not source or not source.content_text:
                raise ValueError("No content_text to chunk")

            text = source.content_text
            segments = self.split_text(text)

            await session.execute(delete(Chunk).where(Chunk.source_id == source_id))

            chunks: list[Chunk] = []
            for idx, seg in enumerate(segments):
                row = Chunk(
                    source_id=source_id,
                    chunk_index=idx,
                    content=seg.content,
                    token_count=seg.token_count,
                    doc_char_start=seg.doc_char_start,
                    doc_char_end=seg.doc_char_end,
                    map_status="pending",
                )
                session.add(row)
                chunks.append(row)

            source.chunked_content_hash = source.content_hash
            await session.commit()
            for row in chunks:
                await session.refresh(row)
            return chunks

    async def chunk_and_embed(self, source_id: int) -> list[Chunk]:
        async with async_session_maker() as session:
            source = await session.get(Source, source_id)
            if not source or not source.content_text:
                raise ValueError("No content_text to chunk")

            text = source.content_text
            segments = self.split_text(text)

            await session.execute(delete(Chunk).where(Chunk.source_id == source_id))

            embed_inputs: list[str] = []
            prefixes: list[str] = []
            for seg in segments:
                prefix = await self._contextual_prefix(text, seg.content)
                prefixes.append(prefix)
                body = f"{prefix}\n\n{seg.content}" if prefix else seg.content
                embed_inputs.append(body)

            embeddings: list[list[float]] = []
            if self.llm and embed_inputs:
                embeddings = await self.llm.embed_texts(embed_inputs)

            chunks: list[Chunk] = []
            for idx, seg in enumerate(segments):
                embedding = embeddings[idx] if idx < len(embeddings) else None
                row = Chunk(
                    source_id=source_id,
                    chunk_index=idx,
                    content=seg.content,
                    contextual_prefix=prefixes[idx] or None,
                    token_count=seg.token_count,
                    doc_char_start=seg.doc_char_start,
                    doc_char_end=seg.doc_char_end,
                    embedding_model=self.settings.embedding_model if embedding else None,
                )
                session.add(row)
                chunks.append(row)

            await session.commit()
            for row in chunks:
                await session.refresh(row)

        # Vector writes go through the store; the PG rows keep only embedding_model.
        await self.vectors.upsert_chunks(
            [
                (row.id, source_id, embeddings[idx])
                for idx, row in enumerate(chunks)
                if idx < len(embeddings) and embeddings[idx] is not None
            ]
        )
        return chunks
