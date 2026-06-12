"""Parallel MAP phase: contextual prefix, extract, glean-loop, batched embed."""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from dataclasses import dataclass
from types import SimpleNamespace

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
from app.services.vector_store import VectorStore, get_vector_store

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
        vector_store: VectorStore | None = None,
    ):
        self.llm = llm_service
        self.settings = settings or get_settings()
        self.chunk_service = chunk_service or ChunkService(llm_service=llm_service, settings=self.settings)
        self.vectors = vector_store or get_vector_store(self.settings)

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

    async def _extract_chunk(self, chunk, full_doc: str) -> ExtractionResult:
        """Extract entities from chunk.content with doc offset = chunk.doc_char_start.

        ``chunk`` may be a real Chunk ORM row or a SimpleNamespace with the same
        attributes (content, doc_char_start, id) — used by map_window for the
        virtual window slice.
        """
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
        chunk,
        round0: ExtractionResult,
        *,
        max_gleanings: int,
    ) -> list[tuple[int, ExtractionResult]]:
        """Run the glean (missed-entity) loop.

        ``chunk`` may be a real Chunk or a SimpleNamespace with .content,
        .doc_char_start, .id — same duck-typed contract as _extract_chunk.
        """
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

    # ------------------------------------------------------------------
    # Core window extraction
    # ------------------------------------------------------------------

    async def map_window(
        self,
        chunk_ids: list[int],
        source_id: int,
        job_id: int | None = None,
    ) -> dict[str, int]:
        """Process a window of chunks as independent consecutive-run extraction calls.

        Algorithm
        ---------
        1. Claim each chunk via CAS (pending|failed → running). Skip those
           already owned by another worker. If NONE claimed, return skipped.
        2. Load source.content_text; split the claimed chunks into runs of
           CONSECUTIVE chunk_index values. Gaps caused by unclaimed chunks
           create separate runs — unclaimed chunks' doc ranges are never
           included in any run's text.
        3–7. Per-run loop (each run is processed and persisted independently):
           3. For each chunk in the run, generate its contextual prefix.
           4. Build run text = content_text[run_first.doc_char_start :
              run_last.doc_char_end]; extract with a single LLM call; offset
              base = run_first.doc_char_start so returned offsets become
              doc-global after += base.
              The run text is sliced from source.content_text (the same text
              doc-global mention offsets are interpreted against — more consistent
              than chunk.content, which is a token-decode snapshot; content_text
              is written once at parse and never mutated).
           5. Optional glean loop (glean_round=1) on the run text.
           6. Demux: each entity is assigned to the FIRST chunk in the run
              whose [doc_char_start, doc_char_end) contains its doc-global
              char_start. Entities with char_start=None or out-of-range →
              first chunk of the run. ALL relationships → first chunk of run.
           7. Write ChunkExtraction rows + mark run chunks MAP_DONE atomically:
              - Round 0: every chunk in the run gets a row (empty or not).
              - Glean rounds (r > 0): only write rows that have content.
              - Delete existing rows before inserting (re-map safe).
           On run failure: mark that run's chunks MAP_FAILED; other runs
           continue unaffected.
        8. If no runs succeeded (all failed), re-raise the last exception.
        """
        if not chunk_ids:
            return {"entities_raw": 0, "relationships_raw": 0, "glean_entities_added": 0, "skipped": 0}

        # --- Step 1: claim each chunk ---
        claimed_ids: list[int] = []
        for cid in chunk_ids:
            if await claim_chunk_for_map(cid):
                claimed_ids.append(cid)

        if not claimed_ids:
            return {
                "entities_raw": 0,
                "relationships_raw": 0,
                "glean_entities_added": 0,
                "skipped": len(chunk_ids),
            }

        # --- Step 2: load source + claimed chunks ---
        try:
            async with async_session_maker() as session:
                source = await session.get(Source, source_id)
                if source is None or not source.content_text:
                    raise ValueError(f"Source {source_id} has no content_text")
                source_text: str = source.content_text

                claimed_chunks = list(
                    (
                        await session.execute(
                            select(Chunk)
                            .where(Chunk.id.in_(claimed_ids))
                            .order_by(Chunk.chunk_index)
                        )
                    )
                    .scalars()
                    .all()
                )

            if not claimed_chunks:
                raise ValueError(f"Claimed chunk IDs {claimed_ids} not found in DB")

        except Exception as exc:
            for cid in claimed_ids:
                await mark_chunk_failed(cid, str(exc))
            raise

        # --- Split claimed chunks into runs of consecutive chunk_index ---
        # Unclaimed chunks create index gaps that break adjacency and start a new run.
        runs: list[list[Chunk]] = []
        current_run: list[Chunk] = [claimed_chunks[0]]
        for chunk in claimed_chunks[1:]:
            if chunk.chunk_index == current_run[-1].chunk_index + 1:
                current_run.append(chunk)
            else:
                runs.append(current_run)
                current_run = [chunk]
        runs.append(current_run)

        # --- Steps 3–7: process each run independently ---
        total_entities_raw = 0
        total_relationships_raw = 0
        total_glean_added = 0
        last_exc: Exception | None = None
        successful_runs = 0

        for run in runs:
            try:
                run_first = run[0]
                run_last = run[-1]

                # Step 3: contextual prefix for each chunk (before extraction so
                # prefix→extract ordering is preserved for K=1, matching legacy tests)
                chunk_prefixes: dict[int, str] = {}
                for chunk in run:
                    prefix = await self.chunk_service._contextual_prefix(
                        source_text, chunk.content
                    )
                    chunk_prefixes[chunk.id] = prefix

                # Step 4: build run text and extract
                offset_base = run_first.doc_char_start
                run_text = source_text[run_first.doc_char_start : run_last.doc_char_end]

                virtual_chunk = SimpleNamespace(
                    content=run_text,
                    doc_char_start=offset_base,
                    id=run_first.id,
                )
                round0 = await self._extract_chunk(virtual_chunk, source_text)

                # Step 5: glean loop on the run text
                glean_rounds = await self._glean_loop(
                    virtual_chunk,
                    round0,
                    max_gleanings=self.settings.ingest_max_gleanings,
                )

                entities_raw = len(round0.entities)
                relationships_raw = len(round0.relationships)
                glean_added = sum(len(g.entities) for _, g in glean_rounds)

                # Step 6: demux entities to per-chunk rows within this run
                run_chunk_ranges = [
                    (c.id, c.doc_char_start, c.doc_char_end) for c in run
                ]
                first_run_chunk_id = run[0].id

                def _owning_chunk_id(char_start: int | None) -> int:
                    """First run-chunk whose [doc_char_start, doc_char_end) contains char_start."""
                    if char_start is None:
                        return first_run_chunk_id
                    for cid, cstart, cend in run_chunk_ranges:
                        if cstart <= char_start < cend:
                            return cid
                    return first_run_chunk_id  # out-of-range → first chunk of run

                all_rounds: list[tuple[int, ExtractionResult]] = [(0, round0)] + glean_rounds

                # round_data[r][chunk_id] = (entities_list, relationships_list)
                round_data: dict[int, dict[int, tuple[list, list]]] = {}
                for r, result in all_rounds:
                    per_ents: dict[int, list] = {c.id: [] for c in run}
                    per_rels: dict[int, list] = {c.id: [] for c in run}
                    for ent in result.entities:
                        owner = _owning_chunk_id(ent.char_start)
                        per_ents[owner].append(ent.model_dump())
                    for rel in result.relationships:
                        per_rels[first_run_chunk_id].append(rel.model_dump())
                    round_data[r] = {
                        c.id: (per_ents[c.id], per_rels[c.id]) for c in run
                    }

                # Step 7 (part A): embed each chunk in this run
                chunk_embeddings: dict[int, list[float] | None] = {}
                for chunk in run:
                    prefix = chunk_prefixes[chunk.id]
                    embed_body = f"{prefix}\n\n{chunk.content}" if prefix else chunk.content
                    embedding: list[float] | None = None
                    if self.llm:
                        embeddings_list = await self.llm.embed_texts([embed_body])
                        embedding = embeddings_list[0] if embeddings_list else None
                    if embedding is None and not self.settings.ingest_allow_null_embedding:
                        raise ValueError(f"Embedding required for chunk {chunk.id}")
                    chunk_embeddings[chunk.id] = embedding

                # Vector writes go through the store; the PG UPDATE below keeps
                # only embedding_model + map status fields.
                await self.vectors.upsert_chunks(
                    [
                        (chunk.id, source_id, chunk_embeddings[chunk.id])
                        for chunk in run
                        if chunk_embeddings[chunk.id] is not None
                    ]
                )

                now = datetime.now(timezone.utc)

                # Step 7 (part B): persist atomically for this run
                async with async_session_maker() as session:
                    # Delete-before-insert (re-map safe)
                    await session.execute(
                        delete(ChunkExtraction).where(
                            ChunkExtraction.chunk_id.in_([c.id for c in run])
                        )
                    )

                    # Round 0: every chunk in run gets a row (empty rows too)
                    for chunk in run:
                        ents, rels = round_data[0][chunk.id]
                        session.add(
                            ChunkExtraction(
                                chunk_id=chunk.id,
                                source_id=source_id,
                                entities=ents,
                                relationships=rels,
                                glean_round=0,
                            )
                        )

                    # Glean rounds: only write rows that have content
                    for r, _ in glean_rounds:
                        for chunk in run:
                            ents, rels = round_data[r][chunk.id]
                            if ents or rels:
                                session.add(
                                    ChunkExtraction(
                                        chunk_id=chunk.id,
                                        source_id=source_id,
                                        entities=ents,
                                        relationships=rels,
                                        glean_round=r,
                                    )
                                )

                    # Mark run chunks MAP_DONE
                    for chunk in run:
                        prefix = chunk_prefixes[chunk.id]
                        embedding = chunk_embeddings[chunk.id]
                        await session.execute(
                            update(Chunk)
                            .where(Chunk.id == chunk.id)
                            .values(
                                contextual_prefix=prefix or None,
                                embedding_model=(
                                    self.settings.embedding_model if embedding else None
                                ),
                                map_status=MAP_DONE,
                                map_last_error=None,
                                mapped_at=now,
                                map_started_at=None,
                            )
                        )

                    if job_id is not None:
                        await touch_job_heartbeat(session, job_id)

                    await session.commit()

                total_entities_raw += entities_raw
                total_relationships_raw += relationships_raw
                total_glean_added += glean_added
                successful_runs += 1

            except Exception as exc:
                last_exc = exc
                for chunk in run:
                    await mark_chunk_failed(chunk.id, str(exc))
                logger.warning(
                    "map_window run %s (source=%s) failed: %s",
                    [c.id for c in run],
                    source_id,
                    exc,
                )

        # Re-raise if no run succeeded (preserves fail-fast behaviour for single-run windows)
        if successful_runs == 0 and last_exc is not None:
            raise last_exc

        return {
            "entities_raw": total_entities_raw,
            "relationships_raw": total_relationships_raw,
            "glean_entities_added": total_glean_added,
        }

    # ------------------------------------------------------------------
    # Single-chunk wrapper (preserves legacy contract for existing callers)
    # ------------------------------------------------------------------

    async def map_single_chunk(
        self,
        chunk_id: int,
        source_id: int,
        *,
        job_id: int | None = None,
    ) -> dict[str, int]:
        """Process one chunk: prefix, extract, glean-loop, embed, persist atomically.

        Delegates to map_window([chunk_id], ...) after handling the MAP_DONE
        fast-path that returns actual stats without claiming.  Return shape and
        LLM call ordering (prefix → extract → glean) are identical to the
        pre-refactor implementation, so existing callers and test scripts are
        unchanged.
        """
        # Fast path: chunk already done — return actual stats without re-processing
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

        # Delegate to map_window for all actual work (claim + extract + persist)
        return await self.map_window([chunk_id], source_id, job_id=job_id)

    # ------------------------------------------------------------------
    # Service-mode batch mapper with window grouping
    # ------------------------------------------------------------------

    async def map_chunks(
        self,
        source_id: int,
        *,
        job_id: int | None = None,
        max_concurrency: int | None = None,
    ) -> dict[str, int | float]:
        """Map pending/failed chunks via parallel workers (service gather mode).

        Chunks are grouped into windows of K consecutive chunk_index values
        (K = settings.ingest_extraction_window_chunks, default 1).  A gap in
        chunk_index breaks a window.  With K=1 behaviour is identical to the
        pre-refactor per-chunk workers.
        """
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

        K = self.settings.ingest_extraction_window_chunks

        def _group_into_windows(chunks_list: list[Chunk], k: int) -> list[list[Chunk]]:
            """Group consecutive-index chunks into windows of at most k."""
            windows: list[list[Chunk]] = []
            current: list[Chunk] = []
            for chunk in chunks_list:
                if not current:
                    current.append(chunk)
                elif (
                    len(current) < k
                    and chunk.chunk_index == current[-1].chunk_index + 1
                ):
                    current.append(chunk)
                else:
                    windows.append(current)
                    current = [chunk]
            if current:
                windows.append(current)
            return windows

        windows = _group_into_windows(chunks, K)

        sem = asyncio.Semaphore(max_concurrency)
        tracker = _ConcurrencyTracker()
        results: list[dict[str, int]] = []

        async def _worker(window_chunks: list[Chunk]) -> dict[str, int]:
            async with sem:
                tracker.enter()
                try:
                    return await self.map_window(
                        chunk_ids=[c.id for c in window_chunks],
                        source_id=source_id,
                        job_id=job_id,
                    )
                finally:
                    tracker.leave()

        gathered = await asyncio.gather(*[_worker(w) for w in windows], return_exceptions=True)
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
