"""Tests for the entity wiki-page mention-count gate (INGEST_WIKI_MIN_MENTIONS).

Gate logic lives in n_wiki → generate_wiki_pages phase of nodes_cognify.py.
Only entities with Entity.mention_count >= settings.ingest_wiki_min_mentions receive
a generated wiki page; the source summary page is always created regardless.

Two tests:
  1. Default gate (min_mentions=2): only the entity with mention_count=2 gets a page.
  2. Knob test (min_mentions=1): both entities (counts 1 and 2) get pages.
"""

from __future__ import annotations

from sqlalchemy import select

from app.core.config import Settings
from app.core.database import async_session_maker
from app.models.entity import Entity, EntityMention
from app.models.wiki import WikiPage
from app.runtime.graphs.nodes.nodes_cognify import make_cognify_nodes
from tests.conftest import run_async
from tests.fixtures.ingest_fixtures import scripted_services


def _seed_entities(source_id: int):
    """Seed two entities for *source_id*:
    - entity_low  (mention_count=1, 1 EntityMention row) — below default threshold
    - entity_high (mention_count=2, 2 EntityMention rows) — at/above default threshold
    Returns (entity_low, entity_high).
    """

    async def _inner():
        async with async_session_maker() as session:
            entity_low = Entity(
                name="Singleton Entity",
                entity_type="concept",
                description="Mentioned only once.",
                mention_count=1,
            )
            entity_high = Entity(
                name="Frequent Entity",
                entity_type="concept",
                description="Mentioned twice across chunks.",
                mention_count=2,
            )
            session.add_all([entity_low, entity_high])
            await session.flush()

            # 1 mention row for entity_low
            session.add(
                EntityMention(
                    entity_id=entity_low.id,
                    source_id=source_id,
                    context="mention of Singleton Entity",
                )
            )
            # 2 mention rows for entity_high (realistic: appeared in 2 chunks)
            session.add(
                EntityMention(
                    entity_id=entity_high.id,
                    source_id=source_id,
                    context="first mention of Frequent Entity",
                )
            )
            session.add(
                EntityMention(
                    entity_id=entity_high.id,
                    source_id=source_id,
                    context="second mention of Frequent Entity",
                )
            )
            await session.commit()
            await session.refresh(entity_low)
            await session.refresh(entity_high)
            return entity_low, entity_high

    return run_async(_inner())


def _get_entity_pages(source_id: int) -> list[WikiPage]:
    """Return non-summary wiki pages for *source_id*."""

    async def _inner():
        async with async_session_maker() as session:
            result = await session.execute(
                select(WikiPage).where(
                    WikiPage.source_id == source_id,
                    WikiPage.page_type != "summary",
                )
            )
            return result.scalars().all()

    return run_async(_inner())


def _run_n_wiki(source_id: int, settings: Settings) -> dict:
    """Build services with *settings* and invoke n_wiki directly."""
    services = scripted_services([], settings=settings)
    nodes = make_cognify_nodes(services)
    n_wiki = nodes["n_wiki"]

    async def _inner():
        return await n_wiki({"source_id": source_id, "job_id": None})

    return run_async(_inner())


def test_wiki_mention_gate_default(create_source):
    """Default gate (min_mentions=2): only the entity with mention_count=2 gets a page."""
    source = create_source(
        status="pending",
        content_text="Singleton Entity and Frequent Entity appear in this document.",
        content_summary="A document about two entities.",
    )

    entity_low, entity_high = _seed_entities(source.id)

    settings = Settings(
        ingest_orchestrator="graph",
        ingest_map_mode="service",
        ingest_wiki_min_mentions=2,
    )
    result = _run_n_wiki(source.id, settings)

    pages = _get_entity_pages(source.id)
    page_titles = {p.title for p in pages}

    assert entity_low.name not in page_titles, (
        f"entity with mention_count=1 must be skipped (gate >=2); "
        f"found pages: {page_titles}"
    )
    assert entity_high.name in page_titles, (
        f"entity with mention_count=2 must get a wiki page; "
        f"found pages: {page_titles}"
    )

    # Verify the skip count surfaced in metrics
    metrics = result.get("wiki_metrics", {})
    assert metrics.get("skipped_low_mention") == 1, (
        f"expected skipped_low_mention=1, got {metrics.get('skipped_low_mention')!r}; "
        f"full metrics: {metrics}"
    )


def test_wiki_mention_gate_knob_min1(create_source):
    """Knob test (min_mentions=1): both entities get wiki pages regardless of count."""
    source = create_source(
        status="pending",
        content_text="Singleton Entity and Frequent Entity appear in this document.",
        content_summary="A document about two entities.",
    )

    entity_low, entity_high = _seed_entities(source.id)

    settings = Settings(
        ingest_orchestrator="graph",
        ingest_map_mode="service",
        ingest_wiki_min_mentions=1,
    )
    result = _run_n_wiki(source.id, settings)

    pages = _get_entity_pages(source.id)
    page_titles = {p.title for p in pages}

    assert entity_low.name in page_titles, (
        f"with min_mentions=1, entity with mention_count=1 must get a page; "
        f"found pages: {page_titles}"
    )
    assert entity_high.name in page_titles, (
        f"with min_mentions=1, entity with mention_count=2 must get a page; "
        f"found pages: {page_titles}"
    )

    metrics = result.get("wiki_metrics", {})
    assert metrics.get("skipped_low_mention") == 0, (
        f"expected skipped_low_mention=0, got {metrics.get('skipped_low_mention')!r}; "
        f"full metrics: {metrics}"
    )
