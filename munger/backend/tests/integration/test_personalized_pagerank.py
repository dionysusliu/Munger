"""personalized_pagerank: seed-biased PPR over entity_edges ranks seed-neighborhood higher."""

from app.core.config import get_settings
from app.core.database import async_session_maker
from app.models.entity import Entity
from app.models.entity_edge import EntityEdge
from app.services.graph_service import GraphService
from tests.conftest import run_async


def _edge(a, b, w):
    lo, hi = (a, b) if a < b else (b, a)
    return EntityEdge(src_entity_id=lo, tgt_entity_id=hi, weight=w, evidence_count=1)


def test_personalized_pagerank_biases_toward_seed():
    async def _setup():
        async with async_session_maker() as s:
            ents = [Entity(name=n, entity_type="concept") for n in ["A", "B", "C", "D"]]
            for e in ents:
                s.add(e)
            await s.flush()
            ids = [e.id for e in ents]
            for i in range(3):
                s.add(_edge(ids[i], ids[i + 1], 5.0))
            await s.commit()
            return ids

    ids = run_async(_setup())
    a, b, c, d = ids
    scores = run_async(GraphService(get_settings()).personalized_pagerank({a: 1.0}))
    assert scores, "PPR returned empty"
    assert scores[a] > scores[d]
    assert scores[b] > scores[d]


def test_personalized_pagerank_empty_seeds_returns_empty():
    assert run_async(GraphService(get_settings()).personalized_pagerank({})) == {}
