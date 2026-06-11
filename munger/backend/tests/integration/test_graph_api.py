"""POST /api/graph/recompute handler — backfill edges + salience + communities."""

from sqlalchemy import text

from app.api.graph import recompute_endpoint
from app.core.database import async_session_maker
from app.models.entity import Entity
from app.models.entity_relationship import EntityRelationship
from tests.conftest import run_async


def test_recompute_endpoint_backfills_edges_salience_communities():
    async def _setup():
        async with async_session_maker() as s:
            a = Entity(name="A", entity_type="concept", mention_count=2)
            b = Entity(name="B", entity_type="concept", mention_count=1)
            s.add(a); s.add(b); await s.flush()
            # old-data scenario: a relationship exists but entity_edges is EMPTY
            s.add(EntityRelationship(source_entity_id=a.id, target_entity_id=b.id,
                                     relationship_type="related", confidence=1.0))
            await s.commit()
            return a.id, b.id

    a_id, _b_id = run_async(_setup())
    out = run_async(recompute_endpoint(rebuild_edges=True))
    assert out["entities"] >= 2 and out["communities"] >= 1
    assert out["edges"] is not None and out["edges"] >= 1  # rebuild_all ran first

    async def _check():
        async with async_session_maker() as s:
            sal = (await s.execute(text("SELECT salience FROM entities WHERE id=:i"), {"i": a_id})).scalar()
            comm = (await s.execute(text("SELECT community_id FROM entities WHERE id=:i"), {"i": a_id})).scalar()
            edges = (await s.execute(text("SELECT count(*) FROM entity_edges"))).scalar()
            return sal, comm, edges

    sal, comm, edges = run_async(_check())
    assert sal is not None and sal > 0
    assert comm is not None
    assert edges >= 1


def test_recompute_endpoint_without_edge_rebuild():
    out = run_async(recompute_endpoint(rebuild_edges=False))
    assert "entities" in out and "communities" in out
    assert out["edges"] is None


def test_graph_route_registered():
    from app.main import app
    paths = {getattr(r, "path", None) for r in app.routes}
    assert "/api/graph/recompute" in paths
