"""POST /api/entities/{resolve,unmerge,label} handlers."""

from sqlalchemy import text

from app.api.resolution import (
    LabelRequest,
    UnmergeRequest,
    label_pair_endpoint,
    resolve_endpoint,
    unmerge_endpoint,
)
from app.core.database import async_session_maker
from app.models.entity import Entity
from tests.conftest import run_async


async def _canon(eid):
    async with async_session_maker() as s:
        return (await s.execute(text("SELECT canonical_entity_id FROM entities WHERE id=:i"), {"i": eid})).scalar()


def test_resolve_and_unmerge_via_handlers():
    async def _setup():
        async with async_session_maker() as s:
            a = Entity(name="Tesla Inc", entity_type="organization", mention_count=9)
            b = Entity(name="Tesla Inc.", entity_type="organization", mention_count=1)
            s.add(a); s.add(b); await s.commit()
            return a.id, b.id

    a_id, b_id = run_async(_setup())
    out = run_async(resolve_endpoint(tau_block=0.4, tau_auto=0.6))
    assert "merged" in out
    assert run_async(_canon(b_id)) == a_id
    run_async(unmerge_endpoint(UnmergeRequest(entity_id=b_id)))
    assert run_async(_canon(b_id)) is None


def test_label_endpoint_records_pair():
    async def _setup():
        async with async_session_maker() as s:
            a = Entity(name="X1", entity_type="concept", mention_count=1)
            b = Entity(name="X2", entity_type="concept", mention_count=1)
            s.add(a); s.add(b); await s.commit()
            return a.id, b.id

    a_id, b_id = run_async(_setup())
    run_async(label_pair_endpoint(LabelRequest(entity_a_id=a_id, entity_b_id=b_id, label="reject")))

    async def _count():
        async with async_session_maker() as s:
            return (await s.execute(text("SELECT count(*) FROM labeled_pairs"))).scalar()

    assert run_async(_count()) == 1


def test_resolution_routes_registered():
    from app.main import app
    paths = {getattr(r, "path", None) for r in app.routes}
    assert "/api/entities/resolve" in paths
    assert "/api/entities/unmerge" in paths
    assert "/api/entities/label" in paths
