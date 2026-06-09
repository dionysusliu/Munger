"""Node factory for the ``cognify`` subgraph: chunk, map, reduce, link, summarize, wiki, finalize."""

from __future__ import annotations

import logging
import re

from langgraph.types import Send
from sqlalchemy import select
from app.runtime.errors import MapIncompleteError
from app.services.chunk_map_status import (
    all_chunks_done,
    chunks_needing_map,
    reclaim_stale_running,
)

from app.core.database import async_session_maker
from app.models.chunk import Chunk
from app.models.entity import Entity, EntityMention
from app.models.source import Source
from app.runtime.context import RuntimeServices
from app.runtime.db_helpers import fail_source, get_source, log_ingestion, update_source_status
from app.runtime.pipeline_events import emit_pipeline_summary, pipeline_step
from app.runtime.state import EntityRef
from app.schemas.wiki import WikiPageCreate

logger = logging.getLogger(__name__)


def make_cognify_nodes(services: RuntimeServices) -> dict:
    """Return a dict of async node functions keyed by node name."""

    # ------------------------------------------------------------------
    # n_chunk
    # ------------------------------------------------------------------

    async def n_chunk(state: dict) -> dict:
        """Ensure chunks exist; fan-out only pending/failed chunks for mapping."""
        source_id: int = state["source_id"]
        job_id: int | None = state.get("job_id")

        async with pipeline_step(
            source_id=source_id, job_id=job_id, step_key="chunk_document"
        ) as metrics:
            await update_source_status(source_id, "chunking")
            if not services.chunk:
                raise ValueError("Chunk service unavailable")

            chunks = await services.chunk.ensure_chunks(source_id)
            chunk_ids = await chunks_needing_map(source_id)

            metrics["chunk_count"] = len(chunks)
            metrics["total_tokens"] = sum(c.token_count for c in chunks)
            metrics["chunks_needing_map"] = len(chunk_ids)

        return {"chunk_ids": chunk_ids, "map_metrics": {}, "map_retry_wave": 0}

    # ------------------------------------------------------------------
    # fanout_chunks — conditional edge function (returns list[Send])
    # ------------------------------------------------------------------

    def fanout_chunks(state: dict) -> list[Send] | str:
        """Return one Send per chunk needing map work, or skip to map gate when none."""
        chunk_ids = state.get("chunk_ids", [])
        if not chunk_ids:
            return "n_map_gate"
        source_id = state["source_id"]
        job_id = state.get("job_id")
        return [
            Send(
                "n_process_chunk",
                {"source_id": source_id, "job_id": job_id, "chunk_id": cid},
            )
            for cid in chunk_ids
        ]

    # ------------------------------------------------------------------
    # n_map_gate + routing
    # ------------------------------------------------------------------

    async def n_map_gate(state: dict) -> dict:
        """Reclaim stale workers and bump retry wave after each map pass."""
        source_id: int = state["source_id"]
        await reclaim_stale_running(source_id, services.settings)
        wave = state.get("map_retry_wave", 0) + 1
        return {"map_retry_wave": wave}

    async def _route_map_gate(state: dict, *, retry_target: str) -> list[Send] | str:
        source_id: int = state["source_id"]
        job_id: int | None = state.get("job_id")
        wave: int = state.get("map_retry_wave", 0)

        if await all_chunks_done(source_id):
            return "n_reduce"

        pending = await chunks_needing_map(source_id)
        if wave >= services.settings.ingest_map_max_waves:
            raise MapIncompleteError(source_id, pending, wave)

        if retry_target == "n_map":
            return "n_map"

        return [
            Send(
                "n_process_chunk",
                {"source_id": source_id, "job_id": job_id, "chunk_id": cid},
            )
            for cid in pending
        ]

    async def route_after_map_gate(state: dict) -> list[Send] | str:
        return await _route_map_gate(state, retry_target="n_process_chunk")

    async def route_after_map_gate_service(state: dict) -> str:
        result = await _route_map_gate(state, retry_target="n_map")
        return result if isinstance(result, str) else "n_map"

    # ------------------------------------------------------------------
    # n_map (service mode: INGEST_MAP_MODE=service)
    # ------------------------------------------------------------------

    async def n_map(state: dict) -> dict:
        """Batch map all chunks via MapChunkService (legacy service-gather mode)."""
        source_id: int = state["source_id"]
        job_id: int | None = state.get("job_id")

        async with pipeline_step(
            source_id=source_id, job_id=job_id, step_key="map_chunks"
        ) as metrics:
            await update_source_status(source_id, "extracting_entities")
            if not services.map_chunks:
                raise ValueError("Map chunk service unavailable")
            stats = await services.map_chunks.map_chunks(source_id, job_id=job_id)
            metrics.update(stats)

        return {"map_metrics": stats}

    # ------------------------------------------------------------------
    # n_reduce
    # ------------------------------------------------------------------

    async def n_reduce(state: dict) -> dict:
        """Exact-dedup + prof-merge via ResolutionService."""
        source_id: int = state["source_id"]
        job_id: int | None = state.get("job_id")

        async with pipeline_step(
            source_id=source_id, job_id=job_id, step_key="reduce_entities"
        ) as metrics:
            if not services.resolution:
                raise ValueError("Resolution service unavailable")
            stats = await services.resolution.reduce_entities(source_id)
            metrics.update(stats)

        return {"reduce_metrics": stats}

    # ------------------------------------------------------------------
    # n_link
    # ------------------------------------------------------------------

    async def n_link(state: dict) -> dict:
        """Cross-chunk entity linking via LinkingService (R-EMB + co-mention)."""
        source_id: int = state["source_id"]
        job_id: int | None = state.get("job_id")

        async with pipeline_step(
            source_id=source_id, job_id=job_id, step_key="link_entities"
        ) as metrics:
            if services.linking is None:
                logger.info("LinkingService not available; skipping n_link for source %s", source_id)
                return {"link_metrics": {}}
            stats = await services.linking.link_source(source_id, job_id=job_id)
            metrics.update(stats)

        return {"link_metrics": stats}

    # ------------------------------------------------------------------
    # n_summarize
    # ------------------------------------------------------------------

    async def n_summarize(state: dict) -> dict:
        """Generate a source summary via LLMService (non-fatal)."""
        source_id: int = state["source_id"]
        job_id: int | None = state.get("job_id")

        async with pipeline_step(
            source_id=source_id, job_id=job_id, step_key="summarize_source"
        ) as metrics:
            await update_source_status(source_id, "summarizing")
            source = await get_source(source_id)
            if not source or not source.content_text:
                return {"summary_chars": 0}
            if not services.llm:
                return {"summary_chars": 0}

            summary = await services.llm.summarize(source.content_text)
            async with async_session_maker() as session:
                row = await session.get(Source, source_id)
                if row:
                    row.content_summary = summary
                    await session.commit()
            metrics["summary_chars"] = len(summary)

        return {"summary_chars": len(summary)}

    # ------------------------------------------------------------------
    # n_wiki  (two pipeline_step emissions: generate_wiki_pages + link_wiki_pages)
    # ------------------------------------------------------------------

    async def n_wiki(state: dict) -> dict:
        """Generate entity wiki pages, then create wikilinks between them."""
        source_id: int = state["source_id"]
        job_id: int | None = state.get("job_id")
        wiki_metrics: dict = {}

        # --- generate_wiki_pages ---
        async with pipeline_step(
            source_id=source_id, job_id=job_id, step_key="generate_wiki_pages"
        ) as m:
            await update_source_status(source_id, "creating_pages")
            source = await get_source(source_id)
            created = 0
            updated = 0
            summary_page_id: int | None = None

            if source and services.wiki and services.llm:
                text = source.content_text or ""
                summary = source.content_summary or ""

                async with async_session_maker() as session:
                    rows = (
                        await session.execute(
                            select(EntityMention, Entity)
                            .join(Entity, Entity.id == EntityMention.entity_id)
                            .where(EntityMention.source_id == source_id)
                        )
                    ).all()

                try:
                    page_content = summary or text[:5000]
                    wiki_content = await services.llm.generate_wiki_page(
                        title=source.title,
                        content=page_content,
                        page_type="summary",
                    )
                    summary_page = await services.wiki.create_page(
                        WikiPageCreate(
                            title=source.title,
                            slug=services.wiki.generate_slug(source.title),
                            content=wiki_content,
                            page_type="summary",
                            source_id=source_id,
                        )
                    )
                    summary_page_id = summary_page.id
                    created += 1
                except Exception as exc:
                    logger.warning("Summary wiki page failed for %s: %s", source_id, exc)

                for mention, entity in rows:
                    excerpt = _excerpt_from_mention(text, mention)
                    citation = f"> {excerpt[:500]}\n\n" if excerpt else ""
                    try:
                        body = await services.llm.generate_wiki_page(
                            title=entity.name,
                            content=excerpt or entity.description or entity.name,
                            page_type=entity.entity_type,
                        )
                        content = f"{citation}{body}"
                        if entity.wiki_page_id:
                            await services.wiki.update_page(entity.wiki_page_id, content=content)
                            updated += 1
                        else:
                            page = await services.wiki.create_page(
                                WikiPageCreate(
                                    title=entity.name,
                                    slug=services.wiki.generate_slug(entity.name),
                                    content=content,
                                    page_type=entity.entity_type,
                                    source_id=source_id,
                                )
                            )
                            if services.entity:
                                await services.entity.update_entity_wiki_page(entity.id, page.id)
                            created += 1
                            if summary_page_id:
                                await services.wiki.create_link(
                                    from_id=summary_page_id,
                                    to_id=page.id,
                                    link_type="reference",
                                    context=f"Entity from {source.title}",
                                )
                    except Exception as exc:
                        logger.warning("Wiki page failed for %s: %s", entity.name, exc)

            m["pages_created"] = created
            m["pages_updated"] = updated
            wiki_metrics.update(m)

        # --- link_wiki_pages ---
        async with pipeline_step(
            source_id=source_id, job_id=job_id, step_key="link_wiki_pages"
        ) as m:
            entities = await _entities_for_source(source_id)
            links = 0
            if services.wiki:
                for entity in entities:
                    if not entity.get("wiki_page_id"):
                        continue
                    for other in entities:
                        if other["id"] == entity["id"] or not other.get("wiki_page_id"):
                            continue
                        pattern = re.compile(re.escape(other["name"]), re.IGNORECASE)
                        page = await services.wiki.get_page(entity["wiki_page_id"])
                        if page and pattern.search(page.content):
                            try:
                                await services.wiki.create_link(
                                    from_id=entity["wiki_page_id"],
                                    to_id=other["wiki_page_id"],
                                    link_type="related",
                                )
                                links += 1
                            except Exception:
                                pass
            m["links_created"] = links
            wiki_metrics.update(m)

        return {"wiki_metrics": wiki_metrics}

    # ------------------------------------------------------------------
    # n_finalize
    # ------------------------------------------------------------------

    async def n_finalize(state: dict) -> dict:
        """Index wiki, set source completed, emit pipeline_summary."""
        source_id: int = state["source_id"]
        job_id: int | None = state.get("job_id")

        async with pipeline_step(
            source_id=source_id, job_id=job_id, step_key="finalize_ingest"
        ) as metrics:
            entities = await _entities_for_source(source_id)
            async with async_session_maker() as session:
                chunk_rows = (
                    await session.execute(
                        select(Chunk).where(Chunk.source_id == source_id)
                    )
                ).scalars().all()
            chunk_n = len(chunk_rows)
            ratio = len(entities) / chunk_n if chunk_n else 0.0
            metrics["entity_count"] = len(entities)
            metrics["chunk_count"] = chunk_n
            metrics["entities_per_chunk"] = round(ratio, 2)

            if services.wiki:
                try:
                    await services.wiki.update_index()
                except Exception as exc:
                    logger.warning("Index update failed: %s", exc)

            await update_source_status(source_id, "completed")
            await log_ingestion(source_id, f"Ingested with {len(entities)} entities")
            await emit_pipeline_summary(
                source_id=source_id,
                job_id=job_id,
                metrics=metrics,
            )

        return {"status": "completed"}

    return {
        "n_chunk": n_chunk,
        "fanout_chunks": fanout_chunks,
        "n_map": n_map,
        "n_map_gate": n_map_gate,
        "route_after_map_gate": route_after_map_gate,
        "route_after_map_gate_service": route_after_map_gate_service,
        "n_reduce": n_reduce,
        "n_link": n_link,
        "n_summarize": n_summarize,
        "n_wiki": n_wiki,
        "n_finalize": n_finalize,
    }


# ------------------------------------------------------------------
# Shared helpers (mirrors ingest_tools.py internals)
# ------------------------------------------------------------------

async def _entities_for_source(source_id: int) -> list[EntityRef]:
    async with async_session_maker() as session:
        result = await session.execute(
            select(Entity)
            .join(EntityMention, EntityMention.entity_id == Entity.id)
            .where(EntityMention.source_id == source_id)
        )
        entities = result.scalars().unique().all()
        return [
            {
                "id": entity.id,
                "name": entity.name,
                "entity_type": entity.entity_type,
                "wiki_page_id": entity.wiki_page_id,
            }
            for entity in entities
        ]


def _excerpt_from_mention(source_text: str, mention: EntityMention) -> str:
    if mention.char_start is not None and mention.char_end is not None:
        return source_text[mention.char_start: mention.char_end]
    return mention.context or ""
