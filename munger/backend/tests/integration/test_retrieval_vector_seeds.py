"""link_seeds adds semantic seeds via entities.embedding ANN (existing HNSW)."""

from app.core.config import get_settings
from app.core.database import async_session_maker
from app.models.entity import Entity
from app.services.retrieval_service import RetrievalService
from tests.conftest import run_async

DIM = 768


def _vec(i, val=1.0):
    v = [0.0] * DIM
    v[i] = val
    return v


def test_vector_seed_links_semantic_neighbor():
    async def _setup():
        async with async_session_maker() as s:
            near = Entity(name="Latticework", entity_type="concept", salience=0.5, embedding=_vec(0))
            far = Entity(name="Unrelated", entity_type="concept", salience=0.5, embedding=_vec(5))
            s.add(near); s.add(far); await s.commit()
            return near.id, far.id

    near_id, far_id = run_async(_setup())
    svc = RetrievalService(get_settings())
    seeds = run_async(svc.link_seeds("zzz", query_vec=_vec(0)))
    assert near_id in seeds
    assert seeds.index(near_id) <= seeds.index(far_id) if far_id in seeds else True


def test_link_seeds_without_vector_is_name_only():
    async def _setup():
        async with async_session_maker() as s:
            e = Entity(name="Latticework", entity_type="concept", salience=0.5, embedding=_vec(0))
            s.add(e); await s.commit()
            return e.id

    e_id = run_async(_setup())
    seeds = run_async(RetrievalService(get_settings()).link_seeds("zzz"))  # no vector, no name match
    assert e_id not in seeds
