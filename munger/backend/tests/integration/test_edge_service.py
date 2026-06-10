"""EdgeService: derived weighted undirected adjacency from entity_relationships."""

from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import async_session_maker
from app.models.entity import Entity
from app.models.entity_edge import EntityEdge
from app.models.entity_relationship import EntityRelationship
from app.services.edge_service import EdgeService
from tests.conftest import run_async


def _mk_entity(session, name):
    e = Entity(name=name, entity_type="concept", description=name)
    session.add(e)
    return e


def test_rebuild_all_aggregates_undirected_weighted_edges(create_source):
    source = create_source(status="completed")

    async def _setup_and_rebuild():
        async with async_session_maker() as session:
            a = _mk_entity(session, "A"); b = _mk_entity(session, "B")
            await session.flush()
            session.add(EntityRelationship(source_entity_id=a.id, target_entity_id=b.id,
                relationship_type="advocates", confidence=0.6, source_id=source.id))
            session.add(EntityRelationship(source_entity_id=b.id, target_entity_id=a.id,
                relationship_type="relates_to", confidence=0.4, source_id=source.id))
            await session.commit()
            ids = (a.id, b.id)
        await EdgeService(get_settings()).rebuild_all()
        async with async_session_maker() as session:
            edges = (await session.execute(select(EntityEdge))).scalars().all()
        return ids, edges

    (a_id, b_id), edges = run_async(_setup_and_rebuild())
    assert len(edges) == 1
    edge = edges[0]
    assert edge.src_entity_id == min(a_id, b_id)
    assert edge.tgt_entity_id == max(a_id, b_id)
    assert abs(edge.weight - 1.0) < 1e-6
    assert edge.evidence_count == 2


def test_update_for_source_recomputes_only_touched_pairs(create_source):
    s1 = create_source(title="S1", status="completed")
    s2 = create_source(title="S2", status="completed")

    async def _go():
        async with async_session_maker() as session:
            a = _mk_entity(session, "AA"); b = _mk_entity(session, "BB"); c = _mk_entity(session, "CC")
            await session.flush()
            session.add(EntityRelationship(source_entity_id=a.id, target_entity_id=b.id,
                relationship_type="r", confidence=1.0, source_id=s1.id))
            session.add(EntityRelationship(source_entity_id=a.id, target_entity_id=c.id,
                relationship_type="r", confidence=1.0, source_id=s2.id))
            await session.commit()
            ids = (a.id, b.id, c.id)
        await EdgeService(get_settings()).update_for_source(s1.id)
        async with async_session_maker() as session:
            edges = (await session.execute(select(EntityEdge))).scalars().all()
        return ids, edges

    (a_id, b_id, c_id), edges = run_async(_go())
    pairs = {(e.src_entity_id, e.tgt_entity_id) for e in edges}
    assert (min(a_id, b_id), max(a_id, b_id)) in pairs
    assert (min(a_id, c_id), max(a_id, c_id)) not in pairs


def test_top_neighbors_returns_both_directions_ordered_by_weight():
    async def _go():
        async with async_session_maker() as session:
            hub = _mk_entity(session, "HUB"); x = _mk_entity(session, "X"); y = _mk_entity(session, "Y")
            await session.flush()
            def pair(p, q, w):
                lo, hi = (p, q) if p < q else (q, p)
                return EntityEdge(src_entity_id=lo, tgt_entity_id=hi, weight=w, evidence_count=1)
            session.add(pair(hub.id, x.id, 5.0)); session.add(pair(hub.id, y.id, 9.0))
            await session.commit()
            ids = (hub.id, x.id, y.id)
        neighbors = await EdgeService(get_settings()).top_neighbors(ids[0], k=10)
        return ids, neighbors

    (hub_id, x_id, y_id), neighbors = run_async(_go())
    ids_in_order = [n["entity_id"] for n in neighbors]
    assert ids_in_order == [y_id, x_id]
    assert neighbors[0]["weight"] == 9.0
