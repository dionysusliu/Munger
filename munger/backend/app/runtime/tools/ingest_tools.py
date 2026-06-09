"""Provenance-first ingest tools (8-step MAP/REDUCE pipeline + aliases)."""

from __future__ import annotations

import logging
import re

from langchain_core.tools import BaseTool, StructuredTool
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.core.database import async_session_maker
from app.models.chunk import Chunk
from app.models.entity import Entity, EntityMention
from app.models.source import Source
from app.runtime.context import RuntimeServices
from app.runtime.db_helpers import fail_source, get_source, log_ingestion, update_source_status
from app.runtime.pipeline_events import (
    INGEST_TOOL_ORDER,
    emit_pipeline_summary,
    pipeline_step,
)
from app.runtime.state import EntityRef
from app.schemas.wiki import WikiPageCreate

logger = logging.getLogger(__name__)


class SourceIdArgs(BaseModel):
    source_id: int = Field(description="ID of the source to process")


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
        return source_text[mention.char_start : mention.char_end]
    return mention.context or ""


def build_ingest_tools(services: RuntimeServices, job_id: int | None = None) -> list[BaseTool]:
    async def parse_document(source_id: int) -> str:
        async with pipeline_step(source_id=source_id, job_id=job_id, step_key="parse_document") as metrics:
            await update_source_status(source_id, "extracting")
            async with async_session_maker() as session:
                result = await session.execute(select(Source).where(Source.id == source_id))
                source = result.scalar_one_or_none()
                if not source:
                    message = f"Source {source_id} not found"
                    await fail_source(source_id, message)
                    raise ValueError(message)

                if source.content_text:
                    metrics["chars"] = len(source.content_text)
                    return f"Extracted {len(source.content_text)} characters (cached)"

                if not services.storage:
                    message = "Storage service not available"
                    await fail_source(source_id, message)
                    raise ValueError(message)

                text = await services.storage.extract_text(source.file_path, source.file_type)
                if not text:
                    message = "No text could be extracted"
                    await fail_source(source_id, message)
                    raise ValueError(message)

                source.content_text = text
                await session.commit()
                metrics["chars"] = len(text)
                return f"Extracted {len(text)} characters"

    async def chunk_document(source_id: int) -> str:
        async with pipeline_step(source_id=source_id, job_id=job_id, step_key="chunk_document") as metrics:
            await update_source_status(source_id, "chunking")
            if not services.chunk:
                raise ValueError("Chunk service unavailable")
            chunks = await services.chunk.split_chunks(source_id)
            metrics["chunk_count"] = len(chunks)
            metrics["total_tokens"] = sum(c.token_count for c in chunks)
            return f"Created {len(chunks)} chunks"

    async def map_chunks(source_id: int) -> str:
        async with pipeline_step(source_id=source_id, job_id=job_id, step_key="map_chunks") as metrics:
            await update_source_status(source_id, "extracting_entities")
            if not services.map_chunks:
                raise ValueError("Map chunk service unavailable")
            stats = await services.map_chunks.map_chunks(source_id, job_id=job_id)
            metrics.update(stats)
            return (
                f"Mapped {stats.get('chunks_processed', 0)} chunks "
                f"({stats.get('entities_raw', 0)} entities, "
                f"glean +{stats.get('glean_entities_added', 0)})"
            )

    async def reduce_entities(source_id: int) -> str:
        async with pipeline_step(source_id=source_id, job_id=job_id, step_key="reduce_entities") as metrics:
            if not services.resolution:
                raise ValueError("Resolution service unavailable")
            stats = await services.resolution.reduce_entities(source_id)
            metrics.update(stats)
            return (
                f"Reduced {stats.get('entities_canonical', 0)} entities, "
                f"{stats.get('mentions_created', 0)} mentions "
                f"(prof merges: {stats.get('prof_merges', 0)})"
            )

    async def extract_entities_from_chunks(source_id: int) -> str:
        return await map_chunks(source_id)

    async def glean_entities(source_id: int) -> str:
        return await map_chunks(source_id)

    async def resolve_entities(source_id: int) -> str:
        return await reduce_entities(source_id)

    async def summarize_source(source_id: int) -> str:
        async with pipeline_step(source_id=source_id, job_id=job_id, step_key="summarize_source") as metrics:
            await update_source_status(source_id, "summarizing")
            source = await get_source(source_id)
            if not source or not source.content_text:
                return "No text available to summarize"
            if not services.llm:
                return "LLM unavailable; skipped summary"
            summary = await services.llm.summarize(source.content_text)
            async with async_session_maker() as session:
                row = await session.get(Source, source_id)
                if row:
                    row.content_summary = summary
                    await session.commit()
            metrics["summary_chars"] = len(summary)
            return f"Summary generated ({len(summary)} chars)"

    async def generate_wiki_pages(source_id: int) -> str:
        async with pipeline_step(source_id=source_id, job_id=job_id, step_key="generate_wiki_pages") as metrics:
            await update_source_status(source_id, "creating_pages")
            source = await get_source(source_id)
            if not source or not services.wiki or not services.llm:
                return "Wiki/LLM services unavailable"

            text = source.content_text or ""
            summary = source.content_summary or ""
            created = 0
            updated = 0

            async with async_session_maker() as session:
                mentions = (
                    await session.execute(
                        select(EntityMention, Entity)
                        .join(Entity, Entity.id == EntityMention.entity_id)
                        .where(EntityMention.source_id == source_id)
                    )
                ).all()

            summary_page_id: int | None = None
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

            for mention, entity in mentions:
                excerpt = _excerpt_from_mention(text, mention)
                citation = f"> {excerpt[:500]}\n\n" if excerpt else ""
                body = await services.llm.generate_wiki_page(
                    title=entity.name,
                    content=excerpt or entity.description or entity.name,
                    page_type=entity.entity_type,
                )
                content = f"{citation}{body}"
                try:
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

            metrics["pages_created"] = created
            metrics["pages_updated"] = updated
            return f"Wiki pages: {created} created, {updated} updated"

    async def link_wiki_pages(source_id: int) -> str:
        async with pipeline_step(source_id=source_id, job_id=job_id, step_key="link_wiki_pages") as metrics:
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
            metrics["links_created"] = links
            return f"Created {links} wiki links"

    async def finalize_ingest(source_id: int) -> str:
        async with pipeline_step(source_id=source_id, job_id=job_id, step_key="finalize_ingest") as metrics:
            entities = await _entities_for_source(source_id)
            async with async_session_maker() as session:
                chunk_count = (
                    await session.execute(select(Chunk).where(Chunk.source_id == source_id))
                ).scalars().all()
            chunk_n = len(chunk_count)
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
            return f"Ingest completed with {len(entities)} entities (entities/chunk={ratio:.1f})"

    async def extract_source_text(source_id: int) -> str:
        return await parse_document(source_id)

    async def extract_entities_from_text(source_id: int) -> str:
        await chunk_document(source_id)
        await map_chunks(source_id)
        return await reduce_entities(source_id)

    async def create_wiki_pages(source_id: int) -> str:
        gen = await generate_wiki_pages(source_id)
        link = await link_wiki_pages(source_id)
        return f"{gen}; {link}"

    def _wrap(name: str, coro):
        return StructuredTool.from_function(
            coroutine=coro,
            name=name,
            description=f"Ingest pipeline step: {name}",
            args_schema=SourceIdArgs,
        )

    core = [
        _wrap("parse_document", parse_document),
        _wrap("chunk_document", chunk_document),
        _wrap("map_chunks", map_chunks),
        _wrap("reduce_entities", reduce_entities),
        _wrap("summarize_source", summarize_source),
        _wrap("generate_wiki_pages", generate_wiki_pages),
        _wrap("link_wiki_pages", link_wiki_pages),
        _wrap("finalize_ingest", finalize_ingest),
        # Deprecated (gating normalization + unit tests)
        _wrap("extract_entities_from_chunks", extract_entities_from_chunks),
        _wrap("glean_entities", glean_entities),
        _wrap("resolve_entities", resolve_entities),
    ]
    aliases = [
        _wrap("extract_source_text", extract_source_text),
        _wrap("extract_entities_from_text", extract_entities_from_text),
        _wrap("create_wiki_pages", create_wiki_pages),
    ]
    return core + aliases
