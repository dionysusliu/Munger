"""resolve()/unmerge()/label_pair(): soft-merge via canonical_entity_id, reversible, HITL-respecting."""

import networkx  # noqa: F401
from sqlalchemy import text

from app.core.config import get_settings
from app.core.database import async_session_maker
from app.models.entity import Entity
from app.models.entity_edge import EntityEdge
from app.services.edge_service import EdgeService
from app.services.entity_resolution_service import EntityResolutionService
from tests.conftest import run_async


def _svc():
    return EntityResolutionService(get_settings())


async def _canon(eid):
    async with async_session_maker() as s:
        return (await s.execute(text("SELECT canonical_entity_id FROM entities WHERE id=:i"), {"i": eid})).scalar()


def test_resolve_merges_near_dup_to_highest_mention():
    async def _setup():
        async with async_session_maker() as s:
            a = Entity(name="Charlie Munger", entity_type="person", mention_count=9)
            b = Entity(name="Charles Munger", entity_type="person", mention_count=2)
            c = Entity(name="Warren Buffett", entity_type="person", mention_count=4)
            s.add(a); s.add(b); s.add(c); await s.commit()
            return a.id, b.id, c.id

    a_id, b_id, c_id = run_async(_setup())
    stats = run_async(_svc().resolve(tau_block=0.4, tau_auto=0.6))
    assert run_async(_canon(b_id)) == a_id
    assert run_async(_canon(a_id)) is None
    assert run_async(_canon(c_id)) is None
    assert stats["merged"] >= 1


def test_labeled_reject_blocks_merge():
    async def _setup():
        async with async_session_maker() as s:
            a = Entity(name="Mercury", entity_type="concept", mention_count=3)
            b = Entity(name="Mercury", entity_type="concept", mention_count=1)
            s.add(a); s.add(b); await s.commit()
            return a.id, b.id

    a_id, b_id = run_async(_setup())
    run_async(_svc().label_pair(a_id, b_id, "reject"))
    run_async(_svc().resolve(tau_block=0.4, tau_auto=0.6))
    assert run_async(_canon(b_id)) is None
    assert run_async(_canon(a_id)) is None


def test_labeled_match_forces_merge_below_threshold():
    async def _setup():
        async with async_session_maker() as s:
            a = Entity(name="JPMorgan", entity_type="organization", mention_count=5)
            b = Entity(name="Chase Bank", entity_type="organization", mention_count=2)
            s.add(a); s.add(b); await s.commit()
            return a.id, b.id

    a_id, b_id = run_async(_setup())
    run_async(_svc().label_pair(a_id, b_id, "match"))
    run_async(_svc().resolve(tau_block=0.4, tau_auto=0.9))
    assert run_async(_canon(b_id)) == a_id


def test_resolve_flattens_cross_run_chains():
    """A second resolve that merges a former canonical must not leave a B->A->D chain."""
    async def _setup():
        async with async_session_maker() as s:
            a = Entity(name="Acme Corp", entity_type="organization", mention_count=5)
            b = Entity(name="Acme Corp.", entity_type="organization", mention_count=2)
            s.add(a); s.add(b); await s.commit()
            return a.id, b.id

    a_id, b_id = run_async(_setup())
    run_async(_svc().resolve(tau_block=0.4, tau_auto=0.55))
    assert run_async(_canon(b_id)) == a_id  # run 1: B -> A

    async def _add_d():
        async with async_session_maker() as s:
            d = Entity(name="Acme Corp Inc", entity_type="organization", mention_count=20)
            s.add(d); await s.commit()
            return d.id

    d_id = run_async(_add_d())
    run_async(_svc().resolve(tau_block=0.4, tau_auto=0.55))  # run 2: A -> D (D higher mention)

    # No chain: B and A must point DIRECTLY to the root D, and D's own canonical is NULL.
    assert run_async(_canon(a_id)) == d_id
    assert run_async(_canon(b_id)) == d_id, "B->A->D chain was not flattened"
    assert run_async(_canon(d_id)) is None


def test_unmerge_reverses():
    async def _setup():
        async with async_session_maker() as s:
            a = Entity(name="Alpha Co", entity_type="organization", mention_count=5)
            b = Entity(name="Alpha Co.", entity_type="organization", mention_count=1)
            s.add(a); s.add(b); await s.commit()
            return a.id, b.id

    a_id, b_id = run_async(_setup())
    run_async(_svc().resolve(tau_block=0.4, tau_auto=0.6))
    assert run_async(_canon(b_id)) == a_id
    run_async(_svc().unmerge(b_id))
    assert run_async(_canon(b_id)) is None


def test_resolve_then_edges_collapse_to_canonical():
    async def _setup():
        async with async_session_maker() as s:
            a = Entity(name="Alphabet Inc", entity_type="organization", mention_count=9)
            b = Entity(name="Alphabet Inc.", entity_type="organization", mention_count=2)
            x = Entity(name="Google", entity_type="organization", mention_count=5)
            s.add(a); s.add(b); s.add(x); await s.flush()
            from app.models.entity_relationship import EntityRelationship
            s.add(EntityRelationship(source_entity_id=b.id, target_entity_id=x.id,
                                     relationship_type="related", confidence=1.0))
            await s.commit()
            return a.id, b.id, x.id

    a_id, b_id, x_id = run_async(_setup())
    run_async(_svc().resolve(tau_block=0.4, tau_auto=0.6))
    run_async(EdgeService(get_settings()).rebuild_all())

    async def _edge_between(p, q):
        lo, hi = (p, q) if p < q else (q, p)
        async with async_session_maker() as s:
            return (await s.execute(text(
                "SELECT 1 FROM entity_edges WHERE src_entity_id=:l AND tgt_entity_id=:h"),
                {"l": lo, "h": hi})).first()

    assert run_async(_edge_between(a_id, x_id)) is not None
    assert run_async(_edge_between(b_id, x_id)) is None
