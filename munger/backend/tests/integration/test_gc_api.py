"""GC endpoints: candidates / prune-orphans / delete."""

from sqlalchemy import text

from app.api.gc import DeleteRequest, candidates_endpoint, delete_endpoint, prune_orphans_endpoint
from app.core.database import async_session_maker
from app.models.entity import Entity, EntityMention
from tests.conftest import run_async


def test_prune_and_delete_endpoints():
    async def _setup():
        async with async_session_maker() as s:
            orphan = Entity(name="OrphanE", entity_type="concept", mention_count=0)
            junk = Entity(name="JunkE", entity_type="concept", mention_count=1, salience=0.0)
            s.add_all([orphan, junk]); await s.commit()
            # Give junk a real mention row so it survives prune_orphans (orphan check uses the
            # mentions TABLE, not the counter column).
            mention = EntityMention(entity_id=junk.id, context="j")
            s.add(mention); await s.commit()
            return orphan.id, junk.id

    orphan_id, junk_id = run_async(_setup())
    pruned = run_async(prune_orphans_endpoint())
    assert pruned["deleted"] >= 1

    cands = run_async(candidates_endpoint(max_mentions=1, limit=10))
    assert any(c["entity_id"] == junk_id for c in cands["candidates"])

    out = run_async(delete_endpoint(DeleteRequest(entity_ids=[junk_id])))
    assert junk_id in out["deleted_ids"]

    async def _gone():
        async with async_session_maker() as s:
            return (await s.execute(text("SELECT 1 FROM entities WHERE id=:i"), {"i": junk_id})).first()

    assert run_async(_gone()) is None


def test_gc_routes_registered():
    from app.main import app
    paths = {getattr(r, "path", None) for r in app.routes}
    assert "/api/gc/candidates" in paths
    assert "/api/gc/prune-orphans" in paths
    assert "/api/gc/delete" in paths
