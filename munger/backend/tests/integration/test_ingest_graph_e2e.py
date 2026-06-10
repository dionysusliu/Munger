"""End-to-end characterization: run the real compiled graph with a scripted LLM, assert each step's outcome.

This is the SP1 parity oracle. If the DBOS spine (SP1) is at parity, the same assertions must hold.

Script ordering rationale
--------------------------
``map_single_chunk`` calls LLM in this order per chunk (service mode):
  1. ``chunk_service._contextual_prefix()`` → ``llm.chat()``          ← consumes script[0]
  2. ``_extract_chunk()``                   → ``llm.chat_structured()`` ← consumes script[1]
  3. ``_glean_loop()`` (disabled via ingest_max_gleanings=0)

So the scripts list must be ``["<prefix text>"] + two_entity_scripts()`` to ensure the
entity-extraction dict lands at script[1].  Gleaning is disabled for full determinism;
this is an explicitly documented legitimate test configuration.

Expected DB counts after a successful full run on the short single-chunk text:
  chunks   = 1   (~13 tokens, well within the 600-token chunk size)
  embedded = 1   (scripted embed_texts always returns [[0.1]*768])
  entities = 2   ("Charlie Munger", "Mental Models" from two_entity_scripts)
  mentions = 2   (one EntityMention per entity, no R-TEXT augmentation needed)
  pages    = 3   (1 summary page + 1 entity page per entity from n_wiki)
"""

from sqlalchemy import func, select

from app.core.config import Settings
from app.core.database import async_session_maker
from app.models.source import Source
from app.models.chunk import Chunk
from app.models.entity import Entity, EntityMention
from app.models.wiki import WikiPage
from app.runtime.graphs.ingest import build_ingest_graph
from tests.conftest import run_async
from tests.fixtures.ingest_fixtures import scripted_services, two_entity_scripts


def _run_graph(source_id: int):
    # Prepend a plain-string "contextual prefix" script at index 0.
    # map_single_chunk calls _contextual_prefix() first (one chat() call),
    # then _extract_chunk() (one chat_structured() call).  Without the prefix
    # entry, the extraction dict would be consumed by the prefix call and
    # extraction would fall back to an empty result (0 entities).
    #
    # Gleaning is set to 0 to avoid the YES/NO gate consuming additional
    # fallback scripts and producing non-deterministic results.
    scripts = ["Munger document context."] + two_entity_scripts()
    settings = Settings(
        ingest_orchestrator="graph",
        ingest_map_mode="service",
        ingest_max_gleanings=0,
    )
    services = scripted_services(scripts, settings=settings)
    graph = build_ingest_graph(services, checkpointer=None)

    async def _inner():
        return await graph.ainvoke(
            {"source_id": source_id, "job_id": None},
            config={"configurable": {"thread_id": f"test-{source_id}"}},
        )

    return run_async(_inner())


def test_full_ingest_reaches_completed_and_populates_graph(create_source):
    source = create_source(
        status="pending",
        content_text="Charlie Munger champions Mental Models as a latticework for decisions.",
    )
    _run_graph(source.id)

    async def _counts():
        async with async_session_maker() as session:
            src = await session.get(Source, source.id)
            chunks = (await session.execute(
                select(func.count()).select_from(Chunk).where(Chunk.source_id == source.id)
            )).scalar()
            entities = (await session.execute(select(func.count()).select_from(Entity))).scalar()
            mentions = (await session.execute(
                select(func.count()).select_from(EntityMention).where(EntityMention.source_id == source.id)
            )).scalar()
            pages = (await session.execute(
                select(func.count()).select_from(WikiPage).where(WikiPage.source_id == source.id)
            )).scalar()
            embedded = (await session.execute(
                select(func.count()).select_from(Chunk).where(
                    Chunk.source_id == source.id, Chunk.embedding.isnot(None)
                )
            )).scalar()
            return src.status, src.content_summary, chunks, entities, mentions, pages, embedded

    status, summary, chunks, entities, mentions, pages, embedded = run_async(_counts())
    assert status == "completed", "finalize_ingest must set source.status=completed"
    assert summary, "summarize_source must populate source.content_summary"
    assert chunks >= 1, "chunk_document must create chunk rows"
    assert embedded == chunks, "map_chunks must embed every chunk"
    assert entities >= 2, "reduce_entities must create the scripted entities"
    assert mentions >= 2, "reduce_entities must create entity_mentions"
    assert pages >= 3, "generate_wiki_pages must create a summary page + one per entity"
