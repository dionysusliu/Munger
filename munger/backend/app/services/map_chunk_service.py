"""Parallel MAP phase: contextual prefix, extract, glean-loop, batched embed."""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from dataclasses import dataclass

from datetime import datetime, timezone

from sqlalchemy import delete, select, update

from app.core.config import Settings, get_settings
from app.core.database import async_session_maker
from app.models.chunk import Chunk
from app.models.chunk_extraction import ChunkExtraction
from app.models.source import Source
from app.schemas.extraction import ExtractionResult, GleanResult
from app.services.chunk_map_status import (
    MAP_DONE,
    claim_chunk_for_map,
    mark_chunk_failed,
)
from app.services.chunk_service import ChunkService
from app.services.ingest_job_service import touch_job_heartbeat
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)

EXTRACT_SYSTEM = """Extract entities and relationships from the chunk text.
Return ONLY JSON matching:
{"entities":[{"name":"...","type":"person|concept|model|...","description":"...","char_start":0,"char_end":0}],
 "relationships":[{"source":"...","target":"...","type":"relates_to","description":"..."}]}
Use document-global char offsets when possible. Include all salient entities."""

GLEAN_YES_NO_SYSTEM = (
    "Were important entities missed in the prior extraction for this chunk? "
    "Answer with exactly YES or NO."
)

GLEAN_CONTINUE_SYSTEM = """Many entities were missed in the first pass. Return ONLY JSON:
{"missed_entities":[...],"missed_relationships":[...],"reasoning":"..."}"""


@dataclass
class _WaveAResult:
    chunk_id: int
    prefix: str
    embed_text: str
    entities_raw: int = 0
    relationships_raw: int = 0
    glean_entities_added: int = 0


@dataclass
class _ConcurrencyTracker:
    current: int = 0
    max_observed: int = 0

    def enter(self) -> None:
        self.current += 1
        self.max_observed = max(self.max_observed, self.current)

    def leave(self) -> None:
        self.current -= 1


class MapChunkService:
    def __init__(
        self,
        llm_service: LLMService | None,
        chunk_service: ChunkService | None = None,
        settings: Settings | None = None,
    ):
        self.llm = llm_service
        self.settings = settings or get_settings()
        self.chunk_service = chunk_service or ChunkService(llm_service=llm_service, settings=self.settings)

    def _parse_json(self, raw: str) -> dict:
        text = raw.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
        return json.loads(text)

    def _parse_yes_no(self, raw: str) -> bool:
        text = raw.strip().upper()
        if text.startswith("YES"):
            return True
        if text.startswith("NO"):
            return False
        return "YES" in text and "NO" not in text

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
        raw = await self.llm.chat_structured(
            messages, ExtractionResult, max_tokens=4096, temperature=0.2
        )
        result = raw if isinstance(raw, ExtractionResult) else ExtractionResult.model_validate(raw)
        for ent in result.entities:
            if ent.char_start is not None:
                ent.char_start += offset
            if ent.char_end is not None:
                ent.char_end += offset
        return result

    async def _glean_loop(
        self,
        chunk: Chunk,
        round0: ExtractionResult,
        *,
        max_gleanings: int,
    ) -> list[tuple[int, ExtractionResult]]:
        if not self.llm or max_gleanings < 1:
            return []

        glean_rounds: list[tuple[int, ExtractionResult]] = []
        known = json.dumps([e.model_dump() for e in round0.entities])

        yes_no_messages = [
            {"role": "system", "content": GLEAN_YES_NO_SYSTEM},
            {
                "role": "user",
                "content": f"Already extracted: {known}\n\nChunk:\n{chunk.content}",
            },
        ]
        try:
            yes_no_raw = await self.llm.chat(yes_no_messages, max_tokens=8, temperature=0.0)
        except Exception as exc:
            logger.warning("Glean YES/NO gate failed for chunk %s: %s", chunk.id, exc)
            return []

        if not self._parse_yes_no(yes_no_raw):
            return []

        continue_messages = [
            {"role": "system", "content": GLEAN_CONTINUE_SYSTEM},
            {
                "role": "user",
                "content": f"Already extracted: {known}\n\nChunk:\n{chunk.content}",
            },
        ]
        try:
            raw = await self.llm.chat_structured(
                continue_messages, GleanResult, max_tokens=2048, temperature=0.2
            )
            glean = raw if isinstance(raw, GleanResult) else GleanResult.model_validate(raw)
            offset = chunk.doc_char_start
            for ent in glean.missed_entities:
                if ent.char_start is not None:
                    ent.char_start += offset
                if ent.char_end is not None:
                    ent.char_end += offset
            if glean.missed_entities or glean.missed_relationships:
                glean_rounds.append(
                    (
                        1,
                        ExtractionResult(
                            entities=glean.missed_entities,
                            relationships=glean.missed_relationships,
                        ),
                    )
                )
        except Exception as exc:
            logger.warning("Glean continue failed for chunk %s: %s", chunk.id, exc)

        return glean_rounds

    async def map_single_chunk(
        self,
        chunk_id: int,
        source_id: int,
        *,
        job_id: int | None = None,
    ) -> dict[str, int]:
        """Process one chunk: prefix, extract, glean-loop, embed, persist atomically."""
        async with async_session_maker() as session:
            chunk = await session.get(Chunk, chunk_id)
            if chunk is None:
                raise ValueError(f"Chunk {chunk_id} not found")
            if chunk.map_status == MAP_DONE:
                extractions = (
                    await session.execute(
                        select(ChunkExtraction).where(ChunkExtraction.chunk_id == chunk_id)
                    )
                ).scalars().all()
                round0 = next((e for e in extractions if e.glean_round == 0), None)
                entities_raw = len(round0.entities or []) if round0 else 0
                rels_raw = len(round0.relationships or []) if round0 else 0
                glean_added = sum(
                    len(e.entities or [])
                    for e in extractions
                    if e.glean_round > 0
                )
                return {
                    "entities_raw": entities_raw,
                    "relationships_raw": rels_raw,
                    "glean_entities_added": glean_added,
                    "skipped": 1,
                }

        if not await claim_chunk_for_map(chunk_id):
            async with async_session_maker() as session:
                chunk = await session.get(Chunk, chunk_id)
                if chunk and chunk.map_status == MAP_DONE:
                    return {"entities_raw": 0, "relationships_raw": 0, "glean_entities_added": 0, "skipped": 1}
            return {"entities_raw": 0, "relationships_raw": 0, "glean_entities_added": 0, "skipped": 1}

        try:
            async with async_session_maker() as session:
                chunk = await session.get(Chunk, chunk_id)
                if chunk is None:
                    raise ValueError(f"Chunk {chunk_id} not found")
                source = await session.get(Source, source_id)
                if source is None or not source.content_text:
                    raise ValueError(f"Source {source_id} has no content_text")
                source_text: str = source.content_text
                chunk_content: str = chunk.content

            # Two independent chains within a chunk: (prefix -> embed) and
            # (extract -> glean-loop). They share no data, so run them concurrently;
            # per-chunk latency drops from sum to max of the two chains.
            async def _prefix_then_embed() -> tuple[str, list[float] | None]:
                prefix = await self.chunk_service._contextual_prefix(source_text, chunk_content)
                embed_body = f"{prefix}\n\n{chunk_content}" if prefix else chunk_content
                embedding: list[float] | None = None
                if self.llm:
                    embeddings = await self.llm.embed_texts([embed_body])
                    embedding = embeddings[0] if embeddings else None
                return prefix, embedding

            async def _extract_then_glean():
                round0 = await self._extract_chunk(chunk, source_text)
                glean_rounds = await self._glean_loop(
                    chunk,
                    round0,
                    max_gleanings=self.settings.ingest_max_gleanings,
                )
                return round0, glean_rounds

            (prefix, embedding), (round0, glean_rounds) = await asyncio.gather(
                _prefix_then_embed(),
                _extract_then_glean(),
            )

            entities_raw = len(round0.entities)
            relationships_raw = len(round0.relationships)
            glean_added = sum(len(g.entities) for _, g in glean_rounds)

            if embedding is None and not self.settings.ingest_allow_null_embedding:
                raise ValueError(f"Embedding required for chunk {chunk_id}")

            now = datetime.now(timezone.utc)
            async with async_session_maker() as session:
                await session.execute(
                    delete(ChunkExtraction).where(ChunkExtraction.chunk_id == chunk_id)
                )
                session.add(
                    ChunkExtraction(
                        chunk_id=chunk_id,
                        source_id=source_id,
                        entities=[e.model_dump() for e in round0.entities],
                        relationships=[r.model_dump() for r in round0.relationships],
                        glean_round=0,
                    )
                )
                for glean_round, glean_result in glean_rounds:
                    session.add(
                        ChunkExtraction(
                            chunk_id=chunk_id,
                            source_id=source_id,
                            entities=[e.model_dump() for e in glean_result.entities],
                            relationships=[r.model_dump() for r in glean_result.relationships],
                            glean_round=glean_round,
                        )
                    )
                await session.execute(
                    update(Chunk)
                    .where(Chunk.id == chunk_id)
                    .values(
                        contextual_prefix=prefix or None,
                        embedding=embedding,
                        embedding_model=self.settings.embedding_model if embedding else None,
                        map_status=MAP_DONE,
                        map_last_error=None,
                        mapped_at=now,
                        map_started_at=None,
                    )
                )
                if job_id is not None:
                    await touch_job_heartbeat(session, job_id)
                await session.commit()

            return {
                "entities_raw": entities_raw,
                "relationships_raw": relationships_raw,
                "glean_entities_added": glean_added,
            }
        except Exception as exc:
            await mark_chunk_failed(chunk_id, str(exc))
            raise

    async def map_chunks(
        self,
        source_id: int,
        *,
        job_id: int | None = None,
        max_concurrency: int | None = None,
    ) -> dict[str, int | float]:
        """Map pending/failed chunks via parallel workers (service gather mode)."""
        max_concurrency = max_concurrency or self.settings.ingest_chunk_worker_concurrency
        start = time.perf_counter()

        from app.services.chunk_map_status import chunks_needing_map

        chunk_ids = await chunks_needing_map(source_id)
        if not chunk_ids:
            async with async_session_maker() as session:
                total = (
                    await session.execute(
                        select(Chunk.id).where(Chunk.source_id == source_id)
                    )
                ).scalars().all()
            return {
                "chunks_processed": len(total),
                "entities_raw": 0,
                "relationships_raw": 0,
                "glean_entities_added": 0,
                "worker_concurrency": max_concurrency,
                "max_observed_concurrency": 0,
                "duration_ms": 0,
            }

        async with async_session_maker() as session:
            chunks = list(
                (
                    await session.execute(
                        select(Chunk).where(Chunk.id.in_(chunk_ids)).order_by(Chunk.chunk_index)
                    )
                ).scalars().all()
            )

        if not chunks:
            return {
                "chunks_processed": 0,
                "entities_raw": 0,
                "relationships_raw": 0,
                "glean_entities_added": 0,
                "worker_concurrency": max_concurrency,
                "max_observed_concurrency": 0,
                "duration_ms": 0,
            }

        sem = asyncio.Semaphore(max_concurrency)
        tracker = _ConcurrencyTracker()
        results: list[dict[str, int]] = []

        async def _worker(chunk: Chunk) -> dict[str, int]:
            async with sem:
                tracker.enter()
                try:
                    return await self.map_single_chunk(
                        chunk_id=chunk.id,
                        source_id=source_id,
                        job_id=job_id,
                    )
                finally:
                    tracker.leave()

        gathered = await asyncio.gather(*[_worker(c) for c in chunks], return_exceptions=True)
        for item in gathered:
            if isinstance(item, Exception):
                logger.warning("map_chunks worker failed: %s", item)
            else:
                results.append(item)

        duration_ms = int((time.perf_counter() - start) * 1000)
        return {
            "chunks_processed": len(chunks),
            "entities_raw": sum(r.get("entities_raw", 0) for r in results),
            "relationships_raw": sum(r.get("relationships_raw", 0) for r in results),
            "glean_entities_added": sum(r.get("glean_entities_added", 0) for r in results),
            "worker_concurrency": max_concurrency,
            "max_observed_concurrency": tracker.max_observed,
            "duration_ms": duration_ms,
        }
