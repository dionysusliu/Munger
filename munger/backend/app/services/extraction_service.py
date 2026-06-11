"""Per-chunk structured extraction and gleaning."""

from __future__ import annotations

import asyncio
import json
import logging
import re

from sqlalchemy import delete, select

from app.core.config import Settings, get_settings
from app.core.database import async_session_maker
from app.models.chunk import Chunk
from app.models.source import Source
from app.models.chunk_extraction import ChunkExtraction
from app.prompts import EXTRACT_SYSTEM, GLEAN_SYSTEM
from app.schemas.extraction import ExtractionResult, GleanResult
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)


class ExtractionService:
    def __init__(self, llm_service: LLMService | None, settings: Settings | None = None):
        self.llm = llm_service
        self.settings = settings or get_settings()

    def _parse_json(self, raw: str) -> dict:
        text = raw.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
        return json.loads(text)

    async def _extract_chunk(self, chunk: Chunk, full_doc: str) -> ExtractionResult:
        if not self.llm:
            return ExtractionResult()
        offset = chunk.doc_char_start
        messages = [
            {"role": "system", "content": EXTRACT_SYSTEM},
            {
                "role": "user",
                "content": f"Document offset base: {offset}\n\nChunk:\n{chunk.content}",
            },
        ]
        structured = await self.llm.chat_structured(
            messages, ExtractionResult, max_tokens=4096, temperature=0.2
        )
        result = (
            structured
            if isinstance(structured, ExtractionResult)
            else ExtractionResult.model_validate(structured)
        )
        for ent in result.entities:
            if ent.char_start is not None:
                ent.char_start += offset
            if ent.char_end is not None:
                ent.char_end += offset
        return result

    async def extract_entities_from_chunks(
        self,
        source_id: int,
        *,
        max_concurrency: int | None = None,
    ) -> dict[str, int]:
        max_concurrency = max_concurrency or self.settings.ingest_chunk_worker_concurrency
        async with async_session_maker() as session:
            source_text = ""
            src = await session.get(Source, source_id)
            if src:
                source_text = src.content_text or ""

            result = await session.execute(
                select(Chunk).where(Chunk.source_id == source_id).order_by(Chunk.chunk_index)
            )
            chunks = list(result.scalars().all())
            await session.execute(
                delete(ChunkExtraction).where(ChunkExtraction.source_id == source_id)
            )
            await session.commit()

        if not chunks:
            return {"chunks_processed": 0, "entities_raw": 0, "relationships_raw": 0}

        sem = asyncio.Semaphore(max_concurrency)
        totals = {"entities_raw": 0, "relationships_raw": 0}

        async def _one(chunk: Chunk) -> None:
            async with sem:
                parsed = await self._extract_chunk(chunk, source_text)
                async with async_session_maker() as session:
                    session.add(
                        ChunkExtraction(
                            chunk_id=chunk.id,
                            source_id=source_id,
                            entities=[e.model_dump() for e in parsed.entities],
                            relationships=[r.model_dump() for r in parsed.relationships],
                            glean_round=0,
                        )
                    )
                    await session.commit()
                totals["entities_raw"] += len(parsed.entities)
                totals["relationships_raw"] += len(parsed.relationships)

        await asyncio.gather(*[_one(c) for c in chunks])
        totals["chunks_processed"] = len(chunks)
        return totals

    async def glean_entities(self, source_id: int, *, max_gleanings: int | None = None) -> dict[str, int]:
        max_gleanings = max_gleanings or self.settings.ingest_max_gleanings
        if max_gleanings < 1 or not self.llm:
            return {"entities_added": 0, "glean_rounds": 0}

        added = 0
        async with async_session_maker() as session:
            chunks = (
                await session.execute(
                    select(Chunk).where(Chunk.source_id == source_id).order_by(Chunk.chunk_index)
                )
            ).scalars().all()

            for chunk in chunks:
                prior = (
                    await session.execute(
                        select(ChunkExtraction).where(
                            ChunkExtraction.chunk_id == chunk.id,
                            ChunkExtraction.glean_round == 0,
                        )
                    )
                ).scalar_one_or_none()
                known = json.dumps(prior.entities if prior else [])
                messages = [
                    {"role": "system", "content": GLEAN_SYSTEM},
                    {
                        "role": "user",
                        "content": f"Already extracted: {known}\n\nChunk:\n{chunk.content}",
                    },
                ]
                try:
                    structured = await self.llm.chat_structured(
                        messages, GleanResult, max_tokens=2048, temperature=0.2
                    )
                    glean = (
                        structured
                        if isinstance(structured, GleanResult)
                        else GleanResult.model_validate(structured)
                    )
                    offset = chunk.doc_char_start
                    for ent in glean.missed_entities:
                        if ent.char_start is not None:
                            ent.char_start += offset
                        if ent.char_end is not None:
                            ent.char_end += offset
                    if glean.missed_entities or glean.missed_relationships:
                        session.add(
                            ChunkExtraction(
                                chunk_id=chunk.id,
                                source_id=source_id,
                                entities=[e.model_dump() for e in glean.missed_entities],
                                relationships=[r.model_dump() for r in glean.missed_relationships],
                                glean_round=1,
                            )
                        )
                        added += len(glean.missed_entities)
                except Exception as exc:
                    logger.warning("Glean failed for chunk %s: %s", chunk.id, exc)
            await session.commit()

        return {"entities_added": added, "glean_rounds": 1 if added else 0}
