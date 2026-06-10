"""Characterize weak/untested service entry points: chunk, link, wiki.

Key findings (confirmed by reading service implementations):

- ChunkService.ensure_chunks(source_id: int) -> list[Chunk]
  Calls split_chunks when the source has no existing chunks or the content hash changed.
  split_chunks sets map_status="pending" on every new Chunk row (chunk_service.py:148).

- LinkingService.link_source(source_id: int, *, job_id=None) -> dict[str, int]
  Precondition: Entity + EntityMention rows for the source must already exist (produced
  by resolution_service.reduce_entities).  Embeds each entity via llm.embed_texts
  (ScriptedLLMService returns [0.1]*768), persists to entities.embedding, and creates
  co-mention EntityRelationship rows.  Returns metrics dict with keys
  "entity_embeddings", "merges", "cross_chunk_links".

- WikiService.create_page(data: WikiPageCreate) -> WikiPage
  WikiPageCreate requires title:str, slug:str (plus optional fields).
  create_page stores a row; if data.slug already exists it delegates to
  _make_unique_slug which appends "-2", "-3", ... (wiki_service.py:354-363).
"""

from __future__ import annotations

from sqlalchemy import select

from app.core.database import async_session_maker
from app.models.chunk import Chunk
from app.models.chunk_extraction import ChunkExtraction
from app.models.entity import Entity, EntityMention
from app.models.wiki import WikiPage
from app.schemas.wiki import WikiPageCreate
from tests.conftest import run_async
from tests.fixtures.ingest_fixtures import scripted_services, two_entity_scripts


# ---------------------------------------------------------------------------
# Test 1: ensure_chunks
# ---------------------------------------------------------------------------


def test_ensure_chunks_creates_chunk_rows(create_source):
    """ensure_chunks splits source text into Chunk rows; each row has map_status='pending'.

    "Sentence one. " repeated 200 times is ~700 tokens.  With the default chunk size of
    600 tokens (config.py:54) the source produces at least one chunk.
    """
    source = create_source(status="pending", content_text=("Sentence one. " * 200))
    services = scripted_services(["prefix"])

    async def _inner():
        await services.chunk.ensure_chunks(source.id)
        async with async_session_maker() as session:
            result = await session.execute(
                select(Chunk).where(Chunk.source_id == source.id)
            )
            return list(result.scalars().all())

    rows = run_async(_inner())
    assert len(rows) >= 1, "ensure_chunks must create at least one Chunk row"
    for c in rows:
        assert c.content and len(c.content) > 0, "chunk content must be non-empty"
        assert c.token_count is not None and c.token_count > 0, (
            "chunk token_count must be positive"
        )
        # Confirmed value: chunk_service.py line 148 sets map_status="pending"
        assert c.map_status == "pending", (
            f"Expected map_status='pending', got '{c.map_status}'"
        )


# ---------------------------------------------------------------------------
# Test 2: link_source
# ---------------------------------------------------------------------------


def test_link_source_populates_entity_embeddings(create_source):
    """link_source embeds entities and persists non-null embeddings to entities.embedding.

    Setup:
      1. Seed a Chunk + ChunkExtraction directly (matching the pattern from
         tests/unit/test_reduce_prof_merge.py).
      2. Run reduce_entities to materialise Entity + EntityMention rows
         (required precondition: link_source JOINs EntityMention on source_id).
      3. Call link_source; assert entity_embeddings >= 1 in the returned metrics and
         that every entity for this source has a non-null embedding in the DB.

    ScriptedLLMService.embed_texts always returns [[0.1]*768, ...] (fake_llm.py:33-34),
    so the assertion is meaningful: a null embedding means _embed_entities never ran.
    """
    content = (
        "Charlie Munger advocates Mental Models. "
        "Mental Models are a latticework of ideas."
    )
    source = create_source(status="pending", content_text=content)
    services = scripted_services(two_entity_scripts())

    async def _seed():
        async with async_session_maker() as session:
            chunk = Chunk(
                source_id=source.id,
                chunk_index=0,
                content=content,
                token_count=20,
                doc_char_start=0,
                doc_char_end=len(content),
                map_status="pending",
            )
            session.add(chunk)
            await session.commit()
            await session.refresh(chunk)

            session.add(
                ChunkExtraction(
                    chunk_id=chunk.id,
                    source_id=source.id,
                    glean_round=0,
                    entities=[
                        {
                            "name": "Charlie Munger",
                            "type": "person",
                            "description": "Investor",
                            "char_start": 0,
                            "char_end": 14,
                        },
                        {
                            "name": "Mental Models",
                            "type": "concept",
                            "description": "Latticework of ideas",
                            "char_start": 25,
                            "char_end": 38,
                        },
                    ],
                    relationships=[
                        {
                            "source": "Charlie Munger",
                            "target": "Mental Models",
                            "type": "advocates",
                            "description": "promotes",
                        }
                    ],
                )
            )
            await session.commit()

    run_async(_seed())
    # Materialise Entity + EntityMention rows required by link_source
    run_async(services.resolution.reduce_entities(source.id))

    metrics = run_async(services.linking.link_source(source.id))
    assert metrics["entity_embeddings"] >= 1, (
        f"link_source should embed at least one entity; got metrics={metrics}"
    )

    async def _check_embeddings():
        async with async_session_maker() as session:
            result = await session.execute(
                select(Entity)
                .join(EntityMention, EntityMention.entity_id == Entity.id)
                .where(EntityMention.source_id == source.id)
                .distinct()
            )
            return list(result.scalars().unique().all())

    entities = run_async(_check_embeddings())
    assert len(entities) >= 1, (
        "After reduce_entities + link_source there must be at least one entity for the source"
    )
    for e in entities:
        assert e.embedding is not None, (
            f"Entity '{e.name}' has no embedding after link_source; _embed_entities must persist it"
        )


# ---------------------------------------------------------------------------
# Test 3: wiki create_page
# ---------------------------------------------------------------------------


def test_wiki_create_page_makes_row_with_unique_slug():
    """create_page stores a WikiPage row; duplicate slug is resolved by appending '-2'.

    WikiPageCreate requires slug:str.  When data.slug already exists in the DB,
    create_page delegates to _make_unique_slug which tries base_slug-2, base_slug-3, …
    until it finds a free slot (wiki_service.py:354-363).
    """
    services = scripted_services([])

    async def _inner():
        data1 = WikiPageCreate(
            title="Shared Title",
            slug="shared-title",
            content="First page content",
            page_type="summary",
        )
        data2 = WikiPageCreate(
            title="Shared Title",
            slug="shared-title",  # intentionally the same slug
            content="Second page with same slug",
            page_type="summary",
        )
        page1 = await services.wiki.create_page(data1)
        page2 = await services.wiki.create_page(data2)
        return page1, page2

    page1, page2 = run_async(_inner())

    # Both pages must be persisted
    assert page1.id is not None
    assert page2.id is not None

    # page1 gets the requested slug unchanged
    assert page1.slug == "shared-title"

    # page2 gets a deduplicated slug (_make_unique_slug appends "-2" first)
    assert page2.slug != page1.slug, "Duplicate slug must be resolved to a different value"
    assert page2.slug == "shared-title-2", (
        f"Expected 'shared-title-2', got '{page2.slug}'"
    )

    # Verify both rows are in the DB under distinct slugs
    async def _verify_db():
        async with async_session_maker() as session:
            result = await session.execute(
                select(WikiPage).where(WikiPage.title == "Shared Title")
            )
            return list(result.scalars().all())

    db_rows = run_async(_verify_db())
    assert len(db_rows) == 2, f"Expected 2 wiki_pages rows, got {len(db_rows)}"
    slugs = {r.slug for r in db_rows}
    assert "shared-title" in slugs
    assert "shared-title-2" in slugs
