"""GraphGCService: orphan detection + safe entity deletion (prune half of self-improvement)."""

from sqlalchemy import text

from app.core.config import get_settings
from app.core.database import async_session_maker
from app.models.entity import Entity, EntityMention
from app.models.entity_relationship import EntityRelationship
from app.models.wiki import WikiPage
from app.services.graph_gc_service import GraphGCService
from tests.conftest import run_async


def _svc():
    return GraphGCService(get_settings())


async def _exists(eid):
    async with async_session_maker() as s:
        return (await s.execute(text("SELECT 1 FROM entities WHERE id=:i"), {"i": eid})).first() is not None


def test_find_orphans_only_unreferenced():
    async def _setup():
        async with async_session_maker() as s:
            orphan = Entity(name="Orphan", entity_type="concept", mention_count=0)
            mentioned = Entity(name="Mentioned", entity_type="concept", mention_count=1)
            related = Entity(name="Related", entity_type="concept", mention_count=0)
            other = Entity(name="Other", entity_type="concept", mention_count=0)
            s.add_all([orphan, mentioned, related, other]); await s.flush()
            s.add(EntityMention(entity_id=mentioned.id, context="x"))
            s.add(EntityRelationship(source_entity_id=related.id, target_entity_id=other.id,
                                     relationship_type="related", confidence=1.0))
            await s.commit()
            return orphan.id, mentioned.id, related.id, other.id

    o_id, m_id, r_id, x_id = run_async(_setup())
    orphans = run_async(_svc().find_orphans())
    assert o_id in orphans
    assert m_id not in orphans and r_id not in orphans and x_id not in orphans


def test_find_orphans_skips_canonical_roots():
    async def _setup():
        async with async_session_maker() as s:
            root = Entity(name="Root", entity_type="concept", mention_count=0)
            member = Entity(name="Member", entity_type="concept", mention_count=0)
            s.add_all([root, member]); await s.flush()
            member.canonical_entity_id = root.id
            s.add(EntityMention(entity_id=member.id, context="m"))
            await s.commit()
            return root.id

    root_id = run_async(_setup())
    assert root_id not in run_async(_svc().find_orphans())


def test_delete_entities_cleans_wiki_and_mentions_and_refuses_roots():
    async def _setup():
        async with async_session_maker() as s:
            page = WikiPage(title="Doomed", slug="doomed", content="x", page_type="entity")
            s.add(page); await s.flush()
            doomed = Entity(name="Doomed", entity_type="concept", mention_count=1, wiki_page_id=page.id)
            root = Entity(name="Root2", entity_type="concept", mention_count=5)
            member = Entity(name="Member2", entity_type="concept", mention_count=1)
            s.add_all([doomed, root, member]); await s.flush()
            member.canonical_entity_id = root.id
            s.add(EntityMention(entity_id=doomed.id, context="d"))
            await s.commit()
            return doomed.id, page.id, root.id

    doomed_id, page_id, root_id = run_async(_setup())
    out = run_async(_svc().delete_entities([doomed_id, root_id]))
    assert doomed_id in out["deleted_ids"]
    assert root_id in out["skipped_canonical_roots"]
    assert not run_async(_exists(doomed_id))
    assert run_async(_exists(root_id))

    async def _leftovers():
        async with async_session_maker() as s:
            page = (await s.execute(text("SELECT 1 FROM wiki_pages WHERE id=:p"), {"p": page_id})).first()
            mention = (await s.execute(text(
                "SELECT 1 FROM entity_mentions WHERE entity_id=:e"), {"e": doomed_id})).first()
            return page, mention

    page_left, mention_left = run_async(_leftovers())
    assert page_left is None and mention_left is None


def test_prune_orphans_end_to_end():
    async def _setup():
        async with async_session_maker() as s:
            a = Entity(name="GoneA", entity_type="concept", mention_count=0)
            b = Entity(name="StaysB", entity_type="concept", mention_count=1)
            s.add_all([a, b]); await s.flush()
            s.add(EntityMention(entity_id=b.id, context="k"))
            await s.commit()
            return a.id, b.id

    a_id, b_id = run_async(_setup())
    out = run_async(_svc().prune_orphans())
    assert out["deleted"] >= 1
    assert not run_async(_exists(a_id))
    assert run_async(_exists(b_id))


def test_gc_candidates_low_value_only_and_never_human_touched():
    async def _setup():
        async with async_session_maker() as s:
            junk = Entity(name="Figure 3", entity_type="concept", mention_count=1, salience=0.0)
            hot = Entity(name="Chord", entity_type="model", mention_count=16, salience=0.9)
            labeled = Entity(name="LabeledOne", entity_type="concept", mention_count=1, salience=0.0)
            partner = Entity(name="Partner", entity_type="concept", mention_count=9, salience=0.5)
            human_rel = Entity(name="HumanRel", entity_type="concept", mention_count=1, salience=0.0)
            s.add_all([junk, hot, labeled, partner, human_rel]); await s.flush()
            lo, hi = sorted([labeled.id, partner.id])
            await s.execute(text(
                "INSERT INTO labeled_pairs (entity_a_id, entity_b_id, label) VALUES (:a,:b,'reject')"),
                {"a": lo, "b": hi})
            await s.execute(text(
                "INSERT INTO entity_relationships (source_entity_id, target_entity_id, relationship_type, "
                "confidence, method, created_at) VALUES (:a,:b,'related',1.0,'human',now())"),
                {"a": human_rel.id, "b": partner.id})
            await s.commit()
            return junk.id, hot.id, labeled.id, human_rel.id

    junk_id, hot_id, labeled_id, human_rel_id = run_async(_setup())
    cands = run_async(_svc().gc_candidates(max_mentions=1, limit=50))
    ids = [c["entity_id"] for c in cands]
    assert junk_id in ids
    assert hot_id not in ids
    assert labeled_id not in ids
    assert human_rel_id not in ids
    junk_row = next(c for c in cands if c["entity_id"] == junk_id)
    assert {"entity_id", "name", "entity_type", "mention_count", "salience"} <= set(junk_row.keys())


def test_prune_orphans_never_deletes_human_labeled():
    """An entity with zero mentions/relationships but a labeled_pairs row is human-touched -> kept."""
    async def _setup():
        async with async_session_maker() as s:
            kept = Entity(name="LabeledOrphan", entity_type="concept", mention_count=0)
            other = Entity(name="OtherSide", entity_type="concept", mention_count=1)
            s.add_all([kept, other]); await s.flush()
            s.add(EntityMention(entity_id=other.id, context="o"))
            lo, hi = sorted([kept.id, other.id])
            await s.execute(text(
                "INSERT INTO labeled_pairs (entity_a_id, entity_b_id, label) VALUES (:a,:b,'reject')"),
                {"a": lo, "b": hi})
            await s.commit()
            return kept.id

    kept_id = run_async(_setup())
    assert kept_id not in run_async(_svc().find_orphans())
    run_async(_svc().prune_orphans())
    assert run_async(_exists(kept_id)), "human-labeled entity must survive auto-prune"


class TestRetention:
    """Age-based retention (settings-gated, default OFF)."""

    @staticmethod
    def _settings(events_days=0, extractions_days=0):
        base = get_settings()
        s = base.model_copy(
            update={
                "retention_ingest_events_days": events_days,
                "retention_chunk_extractions_days": extractions_days,
            }
        )
        return s

    @staticmethod
    async def _seed(create_source_row):
        async with async_session_maker() as s:
            await s.execute(
                text(
                    "INSERT INTO ingest_events (source_id, event_type, payload, created_at) VALUES "
                    "(:sid, 'pipeline_step_complete', '{}', now() - interval '40 days'),"
                    "(:sid, 'pipeline_step_complete', '{}', now())"
                ),
                {"sid": create_source_row.id},
            )
            chunk_id = (
                await s.execute(
                    text(
                        "INSERT INTO chunks (source_id, chunk_index, content, token_count, doc_char_start, doc_char_end, created_at) "
                        "VALUES (:sid, 0, 'c', 1, 0, 1, now()) RETURNING id"
                    ),
                    {"sid": create_source_row.id},
                )
            ).scalar()
            await s.execute(
                text(
                    "INSERT INTO chunk_extractions (chunk_id, source_id, glean_round, entities, relationships, created_at) VALUES "
                    "(:cid, :sid, 0, '[]', '[]', now() - interval '40 days'),"
                    "(:cid, :sid, 1, '[]', '[]', now())"
                ),
                {"cid": chunk_id, "sid": create_source_row.id},
            )
            await s.commit()

    @staticmethod
    async def _counts():
        async with async_session_maker() as s:
            ev = (await s.execute(text("SELECT count(*) FROM ingest_events"))).scalar()
            ex = (await s.execute(text("SELECT count(*) FROM chunk_extractions"))).scalar()
        return ev, ex

    def test_defaults_keep_everything(self, create_source):
        src = create_source(status="completed", content_text="x")
        run_async(self._seed(src))
        before = run_async(self._counts())
        out = run_async(GraphGCService(self._settings()).purge_aged())
        assert out == {"ingest_events_deleted": 0, "chunk_extractions_deleted": 0}
        assert run_async(self._counts()) == before

    def test_aged_rows_purged_fresh_kept(self, create_source):
        src = create_source(status="completed", content_text="x")
        run_async(self._seed(src))
        out = run_async(
            GraphGCService(self._settings(events_days=30, extractions_days=30)).purge_aged()
        )
        assert out["ingest_events_deleted"] >= 1
        assert out["chunk_extractions_deleted"] == 1
        ev, ex = run_async(self._counts())
        async def _fresh_remain():
            async with async_session_maker() as s:
                old_ev = (await s.execute(text(
                    "SELECT count(*) FROM ingest_events WHERE created_at < now() - interval '30 days'"
                ))).scalar()
                old_ex = (await s.execute(text(
                    "SELECT count(*) FROM chunk_extractions WHERE created_at < now() - interval '30 days'"
                ))).scalar()
            return old_ev, old_ex
        assert run_async(_fresh_remain()) == (0, 0)
        assert ev >= 1 and ex >= 1
