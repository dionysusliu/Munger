"""GraphService.recompute: PageRank -> salience, single-level Louvain -> community_id (NetworkX)."""

from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import async_session_maker
from app.models.entity import Entity
from app.models.entity_edge import EntityEdge
from app.services.graph_service import GraphService
from tests.conftest import run_async


def test_recompute_assigns_salience_and_communities():
    async def _setup():
        async with async_session_maker() as session:
            ents = [Entity(name=n, entity_type="concept", description=n) for n in ["A", "B", "C", "D", "E"]]
            for e in ents:
                session.add(e)
            await session.flush()
            ids = [e.id for e in ents]

            def edge(i, j, w):
                a, b = ids[i], ids[j]
                lo, hi = (a, b) if a < b else (b, a)
                return EntityEdge(src_entity_id=lo, tgt_entity_id=hi, weight=w, evidence_count=1)

            # Cluster 1: A-B-C triangle. Cluster 2: D-E. Disconnected components.
            for (i, j) in [(0, 1), (1, 2), (0, 2), (3, 4)]:
                session.add(edge(i, j, 5.0))
            await session.commit()
            return ids

    ids = run_async(_setup())
    metrics = run_async(GraphService(get_settings()).recompute())

    async def _read():
        async with async_session_maker() as session:
            rows = (await session.execute(select(Entity).where(Entity.id.in_(ids)))).scalars().all()
            return {e.id: (e.salience, e.community_id) for e in rows}

    by_id = run_async(_read())
    cA, cB, cC, cD, cE = [by_id[i][1] for i in ids]
    assert cA is not None and cA == cB == cC, "A,B,C must share a community"
    assert cD == cE, "D,E must share a community"
    assert cA != cD, "the two disconnected clusters must be different communities"
    assert all(by_id[i][0] > 0 for i in ids), "PageRank salience must be populated"
    assert metrics["communities"] >= 2


def test_recompute_idempotent(create_source):
    """Two recomputes leave a single fresh communities set (no accumulation)."""
    async def _setup():
        async with async_session_maker() as session:
            a = Entity(name="IA", entity_type="concept"); b = Entity(name="IB", entity_type="concept")
            session.add(a); session.add(b)
            await session.flush()
            lo, hi = (a.id, b.id) if a.id < b.id else (b.id, a.id)
            session.add(EntityEdge(src_entity_id=lo, tgt_entity_id=hi, weight=2.0, evidence_count=1))
            await session.commit()

    run_async(_setup())
    svc = GraphService(get_settings())
    run_async(svc.recompute())
    m2 = run_async(svc.recompute())

    async def _count_comms():
        async with async_session_maker() as session:
            from app.models.community import Community
            return (await session.execute(select(Community))).scalars().all()

    comms = run_async(_count_comms())
    # Both entities are connected -> exactly one community; a second recompute must not accumulate.
    assert len(comms) == m2["communities"], "communities table must reflect only the latest recompute"
