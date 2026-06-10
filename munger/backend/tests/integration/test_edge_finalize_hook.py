"""SP2.1 wiring: finalize_ingest rolls the source's relationships into entity_edges.

Drives the real ingest graph with the scripted services (which now include an
EdgeService); two_entity_scripts() yields one relationship, so finalize's
update_for_source must produce at least one entity_edges row.
"""

from sqlalchemy import select

from app.core.config import Settings
from app.core.database import async_session_maker
from app.models.entity_edge import EntityEdge
from app.runtime.graphs.ingest import build_ingest_graph
from tests.conftest import run_async
from tests.fixtures.ingest_fixtures import scripted_services, two_entity_scripts


def test_finalize_populates_edges_after_ingest(create_source):
    source = create_source(
        status="pending",
        content_text="Charlie Munger champions Mental Models as a latticework.",
    )
    settings = Settings(ingest_orchestrator="graph", ingest_map_mode="service", ingest_max_gleanings=0)
    services = scripted_services(["prefix"] + two_entity_scripts(), settings=settings)
    # The scripted services must now carry an EdgeService (RuntimeServices.from_settings).
    assert services.edges is not None
    graph = build_ingest_graph(services, checkpointer=None)

    async def _go():
        await graph.ainvoke(
            {"source_id": source.id, "job_id": None},
            config={"configurable": {"thread_id": f"edges-{source.id}"}},
        )
        async with async_session_maker() as session:
            return (await session.execute(select(EntityEdge))).scalars().all()

    edges = run_async(_go())
    assert len(edges) >= 1, "finalize_ingest must roll the source's relationships into entity_edges"
