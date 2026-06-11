"""GraphService.shortest_path: the cross-domain bridge over entity_edges."""

from app.core.config import get_settings
from app.core.database import async_session_maker
from app.models.entity import Entity
from app.models.entity_edge import EntityEdge
from app.services.graph_service import GraphService
from tests.conftest import run_async


def _edge(a, b, w=3.0):
    lo, hi = (a, b) if a < b else (b, a)
    return EntityEdge(src_entity_id=lo, tgt_entity_id=hi, weight=w, evidence_count=1)


def test_shortest_path_finds_bridge():
    async def _setup():
        async with async_session_maker() as s:
            ents = [Entity(name=n, entity_type="concept") for n in ["A", "X", "B", "Z"]]
            for e in ents:
                s.add(e)
            await s.flush()
            a, x, b, z = [e.id for e in ents]
            s.add(_edge(a, x)); s.add(_edge(x, b))  # A-X-B connected; Z isolated
            await s.commit()
            return a, x, b, z

    a, x, b, z = run_async(_setup())
    path = run_async(GraphService(get_settings()).shortest_path(a, b))
    assert path[0] == a and path[-1] == b and x in path
    assert run_async(GraphService(get_settings()).shortest_path(a, z)) == []  # disconnected
    assert run_async(GraphService(get_settings()).shortest_path(a, 999999)) == []  # absent node
