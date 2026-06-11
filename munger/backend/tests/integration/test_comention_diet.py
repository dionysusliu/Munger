"""Co-mention diet: verify extract-only mention filtering and min-shared-chunk threshold.

Three tests covering the two new knobs introduced by the linking-diet feature:
  - INGEST_COMENTION_MIN_CHUNKS (default 2) — pairs need ≥N shared chunks to get an edge.
  - mention_method filter — only 'extract' mentions vote; 'link_text' mentions are ignored.
"""

from __future__ import annotations

from sqlalchemy import func, select

from app.core.config import Settings
from app.core.database import async_session_maker
from app.models.chunk import Chunk
from app.models.entity import Entity, EntityMention
from app.models.entity_relationship import EntityRelationship
from app.models.source import Source
from app.services.linking_service import LinkingService
from tests.conftest import run_async


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_source(session) -> Source:
    src = Source(
        title="diet-test",
        filename="diet.txt",
        file_path="sources/diet.txt",
        file_type="txt",
        content_hash="h-diet-test",
        file_size=1,
        status="completed",
    )
    session.add(src)
    return src


def _chunk(src_id: int, idx: int) -> Chunk:
    return Chunk(
        source_id=src_id,
        chunk_index=idx,
        content=f"chunk content {idx}",
        token_count=10,
        doc_char_start=0,
        doc_char_end=20,
    )


def _mention(entity_id: int, source_id: int, chunk_id: int, method: str = "extract") -> EntityMention:
    return EntityMention(
        entity_id=entity_id,
        source_id=source_id,
        chunk_id=chunk_id,
        mention_method=method,
    )


def _svc(min_chunks: int = 2) -> LinkingService:
    settings = Settings(
        INGEST_COMENTION_MIN_CHUNKS=min_chunks,
    )
    return LinkingService(settings=settings)


# ---------------------------------------------------------------------------
# Test 1: min-shared-chunks threshold
# ---------------------------------------------------------------------------


def test_pairs_require_min_shared_chunks():
    """Pair (A,B) sharing 2 chunks gets an edge; (A,C) sharing only 1 chunk does not.

    Entities:
      A: appears in chunks 1 AND 2 (extract mentions)
      B: appears in chunks 1 AND 2 (extract mentions)  → 2 shared with A → edge expected
      C: appears in chunk 3 only (extract mention)      → 1 shared with A → NO edge
    """
    async def _setup():
        async with async_session_maker() as s:
            src = _make_source(s)
            await s.flush()

            ea = Entity(name="Alpha", entity_type="concept")
            eb = Entity(name="Beta", entity_type="concept")
            ec = Entity(name="Gamma", entity_type="concept")
            s.add(ea); s.add(eb); s.add(ec)
            await s.flush()

            c1 = _chunk(src.id, 0); c2 = _chunk(src.id, 1); c3 = _chunk(src.id, 2)
            s.add(c1); s.add(c2); s.add(c3)
            await s.flush()

            # A appears in chunks 1 and 2
            s.add(_mention(ea.id, src.id, c1.id))
            s.add(_mention(ea.id, src.id, c2.id))
            # B appears in chunks 1 and 2 — shares both with A
            s.add(_mention(eb.id, src.id, c1.id))
            s.add(_mention(eb.id, src.id, c2.id))
            # C appears only in chunk 3 — shares only chunk 3 with nobody above,
            # and shares 0 chunks with A/B. But add A also in chunk3? No — per plan:
            # A&C share only chunk 3 → add A also in chunk 3 so they share 1.
            s.add(_mention(ea.id, src.id, c3.id))
            s.add(_mention(ec.id, src.id, c3.id))
            await s.commit()

            return src.id, ea.id, eb.id, ec.id

    src_id, ea_id, eb_id, ec_id = run_async(_setup())

    count = run_async(_svc(min_chunks=2)._link_by_co_mention(src_id, []))

    async def _check():
        async with async_session_maker() as s:
            # (A,B) edge must exist
            ab = (await s.execute(
                select(func.count()).select_from(EntityRelationship).where(
                    EntityRelationship.source_id == src_id,
                    EntityRelationship.method == "co_mention",
                    ((EntityRelationship.source_entity_id == ea_id) &
                     (EntityRelationship.target_entity_id == eb_id)) |
                    ((EntityRelationship.source_entity_id == eb_id) &
                     (EntityRelationship.target_entity_id == ea_id)),
                )
            )).scalar()

            # (A,C) edge must NOT exist (only 1 shared chunk)
            ac = (await s.execute(
                select(func.count()).select_from(EntityRelationship).where(
                    EntityRelationship.source_id == src_id,
                    EntityRelationship.method == "co_mention",
                    ((EntityRelationship.source_entity_id == ea_id) &
                     (EntityRelationship.target_entity_id == ec_id)) |
                    ((EntityRelationship.source_entity_id == ec_id) &
                     (EntityRelationship.target_entity_id == ea_id)),
                )
            )).scalar()

            return ab, ac

    ab_count, ac_count = run_async(_check())
    assert ab_count == 1, f"Expected 1 (A,B) co_mention edge; got {ab_count}"
    assert ac_count == 0, f"Expected 0 (A,C) co_mention edge (only 1 shared chunk); got {ac_count}"


# ---------------------------------------------------------------------------
# Test 2: link_text mentions do not vote
# ---------------------------------------------------------------------------


def test_link_text_mentions_do_not_vote():
    """Pair (A,B) where B's chunk mentions are all 'link_text' produces NO edge.

    A has 'extract' mentions in chunks 1 and 2.
    B has 'link_text' mentions in chunks 1 and 2.

    Under the diet filter, only 'extract' mentions are counted. B has zero
    extract mentions, so the pair never meets the min-shared-chunks threshold.
    """
    async def _setup():
        async with async_session_maker() as s:
            src = _make_source(s)
            await s.flush()

            ea = Entity(name="Solar", entity_type="concept")
            eb = Entity(name="Panel", entity_type="concept")
            s.add(ea); s.add(eb)
            await s.flush()

            c1 = _chunk(src.id, 0); c2 = _chunk(src.id, 1)
            s.add(c1); s.add(c2)
            await s.flush()

            # A: extract mentions in both chunks
            s.add(_mention(ea.id, src.id, c1.id, method="extract"))
            s.add(_mention(ea.id, src.id, c2.id, method="extract"))
            # B: link_text mentions only — should NOT count
            s.add(_mention(eb.id, src.id, c1.id, method="link_text"))
            s.add(_mention(eb.id, src.id, c2.id, method="link_text"))
            await s.commit()

            return src.id, ea.id, eb.id

    src_id, ea_id, eb_id = run_async(_setup())

    run_async(_svc(min_chunks=2)._link_by_co_mention(src_id, []))

    async def _check():
        async with async_session_maker() as s:
            return (await s.execute(
                select(func.count()).select_from(EntityRelationship).where(
                    EntityRelationship.source_id == src_id,
                    EntityRelationship.method == "co_mention",
                )
            )).scalar()

    edge_count = run_async(_check())
    assert edge_count == 0, (
        f"Expected 0 co_mention edges when B only has link_text mentions; got {edge_count}"
    )


# ---------------------------------------------------------------------------
# Test 3: knob=1 restores legacy single-shared-chunk behaviour
# ---------------------------------------------------------------------------


def test_min_chunks_one_restores_legacy():
    """Setting INGEST_COMENTION_MIN_CHUNKS=1 creates an edge for A&C sharing only 1 chunk.

    Same setup as test 1: A in chunk 1 and chunk 3; C only in chunk 3 (1 shared chunk).
    With the knob set to 1 the single shared chunk is sufficient → edge is created.
    """
    async def _setup():
        async with async_session_maker() as s:
            src = _make_source(s)
            await s.flush()

            ea = Entity(name="Hydrogen", entity_type="concept")
            ec = Entity(name="Oxygen", entity_type="concept")
            s.add(ea); s.add(ec)
            await s.flush()

            c1 = _chunk(src.id, 0); c3 = _chunk(src.id, 1)
            s.add(c1); s.add(c3)
            await s.flush()

            # A in both chunks; C only in chunk3 → 1 shared chunk
            s.add(_mention(ea.id, src.id, c1.id, method="extract"))
            s.add(_mention(ea.id, src.id, c3.id, method="extract"))
            s.add(_mention(ec.id, src.id, c3.id, method="extract"))
            await s.commit()

            return src.id, ea.id, ec.id

    src_id, ea_id, ec_id = run_async(_setup())

    # Use knob=1 — legacy behavior restored
    run_async(_svc(min_chunks=1)._link_by_co_mention(src_id, []))

    async def _check():
        async with async_session_maker() as s:
            return (await s.execute(
                select(func.count()).select_from(EntityRelationship).where(
                    EntityRelationship.source_id == src_id,
                    EntityRelationship.method == "co_mention",
                    ((EntityRelationship.source_entity_id == ea_id) &
                     (EntityRelationship.target_entity_id == ec_id)) |
                    ((EntityRelationship.source_entity_id == ec_id) &
                     (EntityRelationship.target_entity_id == ea_id)),
                )
            )).scalar()

    edge_count = run_async(_check())
    assert edge_count == 1, (
        f"With INGEST_COMENTION_MIN_CHUNKS=1, a single shared chunk should produce an edge; "
        f"got {edge_count}"
    )
