"""EntityResolutionService blocking + scoring."""

from app.core.config import get_settings
from app.core.database import async_session_maker
from app.models.entity import Entity
from app.models.entity_edge import EntityEdge
from app.services.entity_resolution_service import EntityResolutionService
from tests.conftest import run_async

DIM = 768


def _emb(seed: float) -> list[float]:
    v = [0.0] * DIM
    v[0] = seed
    v[1] = 1.0 - seed
    return v


def _svc():
    return EntityResolutionService(get_settings())


def test_block_finds_near_duplicate_same_type():
    async def _setup():
        async with async_session_maker() as s:
            for n in ["Charlie Munger", "Charles Munger", "Warren Buffett"]:
                s.add(Entity(name=n, entity_type="person", mention_count=1))
            await s.commit()

    run_async(_setup())
    pairs = run_async(_svc()._block_candidates(tau_block=0.4))
    names = run_async(_pair_names(pairs))
    assert {"Charlie Munger", "Charles Munger"} in [set(p) for p in names]
    assert not any("Warren Buffett" in p for p in names)


def test_block_excludes_already_merged_and_cross_type():
    async def _setup():
        async with async_session_maker() as s:
            a = Entity(name="Apple Inc", entity_type="organization", mention_count=1)
            b = Entity(name="Apple Inc.", entity_type="organization", mention_count=1)
            c = Entity(name="Apple", entity_type="concept", mention_count=1)  # different type
            s.add(a); s.add(b); s.add(c); await s.flush()
            b.canonical_entity_id = a.id  # already merged -> excluded
            await s.commit()

    run_async(_setup())
    pairs = run_async(_svc()._block_candidates(tau_block=0.4))
    assert pairs == [] or all("Apple" not in n for p in run_async(_pair_names(pairs)) for n in p)


def test_score_combines_name_and_neighbors():
    async def _setup():
        async with async_session_maker() as s:
            a = Entity(name="Charlie Munger", entity_type="person", mention_count=1, embedding=_emb(0.9))
            b = Entity(name="Charles Munger", entity_type="person", mention_count=1, embedding=_emb(0.88))
            x = Entity(name="Berkshire", entity_type="organization", mention_count=1)
            s.add(a); s.add(b); s.add(x); await s.flush()
            for e in (a.id, b.id):
                lo, hi = (e, x.id) if e < x.id else (x.id, e)
                s.add(EntityEdge(src_entity_id=lo, tgt_entity_id=hi, weight=3.0, evidence_count=1))
            await s.commit()
            return a.id, b.id

    a_id, b_id = run_async(_setup())
    score = run_async(_svc().score_ids(a_id, b_id))
    assert 0.0 <= score <= 1.0
    assert score >= 0.7


async def _pair_names(pairs):
    from sqlalchemy import text
    async with async_session_maker() as s:
        out = []
        for a, b in pairs:
            na = (await s.execute(text("SELECT name FROM entities WHERE id=:i"), {"i": a})).scalar()
            nb = (await s.execute(text("SELECT name FROM entities WHERE id=:i"), {"i": b})).scalar()
            out.append((na, nb))
        return out
