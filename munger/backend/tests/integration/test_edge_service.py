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


# ---------------------------------------------------------------------------
# NEW TESTS — coverage gaps identified by independent review
# ---------------------------------------------------------------------------


def test_update_for_source_multisource_weight(create_source):
    """update_for_source must recompute from ALL evidence, not just the given source.

    Pair (A,B) has evidence from both s1 (conf 1.0) and s2 (conf 1.0).
    Calling update_for_source(s1) must produce weight=2.0, not 1.0.
    """
    s1 = create_source(title="MS-S1", status="completed")
    s2 = create_source(title="MS-S2", status="completed")

    async def _go():
        async with async_session_maker() as session:
            a = _mk_entity(session, "MS-A"); b = _mk_entity(session, "MS-B")
            await session.flush()
            session.add(EntityRelationship(
                source_entity_id=a.id, target_entity_id=b.id,
                relationship_type="r", confidence=1.0, source_id=s1.id))
            session.add(EntityRelationship(
                source_entity_id=a.id, target_entity_id=b.id,
                relationship_type="r", confidence=1.0, source_id=s2.id))
            await session.commit()
            ids = (a.id, b.id)
        # entity_edges starts empty; update via s1 only — must still see s2 evidence
        await EdgeService(get_settings()).update_for_source(s1.id)
        async with async_session_maker() as session:
            edges = (await session.execute(select(EntityEdge))).scalars().all()
        return ids, edges

    (a_id, b_id), edges = run_async(_go())
    assert len(edges) == 1, "Expected exactly one edge for pair (A,B)"
    edge = edges[0]
    assert edge.src_entity_id == min(a_id, b_id)
    assert edge.tgt_entity_id == max(a_id, b_id)
    # weight must be sum of BOTH sources' contributions (1.0 + 1.0 = 2.0)
    assert abs(edge.weight - 2.0) < 1e-6, (
        f"weight={edge.weight!r}: update_for_source must aggregate ALL evidence, not just the source's"
    )
    assert edge.evidence_count == 2


def test_update_for_source_leaves_untouched_pairs_intact(create_source):
    """Pairs not touched by source S must survive update_for_source(S) unchanged."""
    s1 = create_source(title="UT-S1", status="completed")
    s2 = create_source(title="UT-S2", status="completed")

    async def _go():
        async with async_session_maker() as session:
            a = _mk_entity(session, "UT-A"); b = _mk_entity(session, "UT-B"); c = _mk_entity(session, "UT-C")
            await session.flush()
            # s1 touches (A,B); s2 touches (A,C)
            session.add(EntityRelationship(
                source_entity_id=a.id, target_entity_id=b.id,
                relationship_type="r", confidence=0.5, source_id=s1.id))
            session.add(EntityRelationship(
                source_entity_id=a.id, target_entity_id=c.id,
                relationship_type="r", confidence=0.7, source_id=s2.id))
            await session.commit()
            ids = (a.id, b.id, c.id)
        # Seed both edges via full rebuild
        await EdgeService(get_settings()).rebuild_all()
        # Now incrementally refresh only s1's pairs
        await EdgeService(get_settings()).update_for_source(s1.id)
        async with async_session_maker() as session:
            edges = (await session.execute(select(EntityEdge))).scalars().all()
        return ids, edges

    (a_id, b_id, c_id), edges = run_async(_go())
    by_pair = {(e.src_entity_id, e.tgt_entity_id): e for e in edges}
    ab_key = (min(a_id, b_id), max(a_id, b_id))
    ac_key = (min(a_id, c_id), max(a_id, c_id))
    assert ab_key in by_pair, "(A,B) edge must exist after update"
    assert ac_key in by_pair, "(A,C) edge must survive — it is NOT touched by s1"
    assert abs(by_pair[ac_key].weight - 0.7) < 1e-6, "(A,C) weight must be unchanged"


def test_rebuild_all_idempotent(create_source):
    """rebuild_all() called twice must produce identical rows."""
    source = create_source(title="Idem-src", status="completed")

    async def _go():
        async with async_session_maker() as session:
            a = _mk_entity(session, "ID-A"); b = _mk_entity(session, "ID-B")
            await session.flush()
            session.add(EntityRelationship(
                source_entity_id=a.id, target_entity_id=b.id,
                relationship_type="r", confidence=0.9, source_id=source.id))
            await session.commit()
        svc = EdgeService(get_settings())
        count1 = await svc.rebuild_all()
        count2 = await svc.rebuild_all()
        async with async_session_maker() as session:
            edges = (await session.execute(select(EntityEdge))).scalars().all()
        return count1, count2, edges

    count1, count2, edges = run_async(_go())
    assert count1 == count2 == 1
    assert abs(edges[0].weight - 0.9) < 1e-6


def test_update_for_source_idempotent(create_source):
    """update_for_source(id) called twice must produce identical rows."""
    source = create_source(title="IdemU-src", status="completed")

    async def _go():
        async with async_session_maker() as session:
            a = _mk_entity(session, "IU-A"); b = _mk_entity(session, "IU-B")
            await session.flush()
            session.add(EntityRelationship(
                source_entity_id=a.id, target_entity_id=b.id,
                relationship_type="r", confidence=0.3, source_id=source.id))
            await session.commit()
        svc = EdgeService(get_settings())
        count1 = await svc.update_for_source(source.id)
        count2 = await svc.update_for_source(source.id)
        async with async_session_maker() as session:
            edges = (await session.execute(select(EntityEdge))).scalars().all()
        return count1, count2, edges

    count1, count2, edges = run_async(_go())
    assert count1 == count2 == 1
    assert abs(edges[0].weight - 0.3) < 1e-6


def test_null_confidence_contributes_one(create_source):
    """A relationship row with confidence=NULL must contribute 1.0 to the edge weight."""
    source = create_source(title="NullConf-src", status="completed")

    async def _go():
        async with async_session_maker() as session:
            a = _mk_entity(session, "NC-A"); b = _mk_entity(session, "NC-B")
            await session.flush()
            # confidence is deliberately None
            session.add(EntityRelationship(
                source_entity_id=a.id, target_entity_id=b.id,
                relationship_type="r", confidence=None, source_id=source.id))
            await session.commit()
        await EdgeService(get_settings()).rebuild_all()
        async with async_session_maker() as session:
            edges = (await session.execute(select(EntityEdge))).scalars().all()
        return edges

    edges = run_async(_go())
    assert len(edges) == 1
    assert abs(edges[0].weight - 1.0) < 1e-6, (
        f"NULL confidence must contribute 1.0 via COALESCE, got weight={edges[0].weight!r}"
    )


def test_top_neighbors_respects_k_limit():
    """top_neighbors(entity_id, k) must return at most k results."""
    async def _go():
        async with async_session_maker() as session:
            hub = _mk_entity(session, "K-HUB")
            neighbors_raw = [_mk_entity(session, f"K-N{i}") for i in range(5)]
            await session.flush()
            for i, n in enumerate(neighbors_raw):
                lo, hi = (hub.id, n.id) if hub.id < n.id else (n.id, hub.id)
                session.add(EntityEdge(src_entity_id=lo, tgt_entity_id=hi,
                                       weight=float(i + 1), evidence_count=1))
            await session.commit()
            hub_id = hub.id
        return await EdgeService(get_settings()).top_neighbors(hub_id, k=3)

    results = run_async(_go())
    assert len(results) == 3
    # Results must be ordered descending by weight
    weights = [r["weight"] for r in results]
    assert weights == sorted(weights, reverse=True)
