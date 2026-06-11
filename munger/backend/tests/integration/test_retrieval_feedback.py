"""Rating consumer (SP4.3): 👍/👎 on chat answers nudges retrieval ranking of cited entities."""

import json

from sqlalchemy import text

from app.core.config import get_settings
from app.core.database import async_session_maker
from app.models.chat_message import ChatMessage
from app.models.chat_session import ChatSession
from app.models.chunk import Chunk
from app.models.entity import Entity, EntityMention
from app.models.source import Source
from app.services.retrieval_service import RetrievalService
from tests.conftest import run_async

DIM = 768


def _vec(i, v=1.0):
    out = [0.0] * DIM
    out[i] = v
    return out


class _FakeEmbedLLM:
    """Query embeds to e0; chunk A at small angle (closer), chunk B exact -> B ranks first."""

    async def embed_text(self, q):
        return _vec(0)


def _rate_citing(entity_id: int, rating: int):
    async def _inner():
        async with async_session_maker() as s:
            sess = ChatSession(title="t"); s.add(sess); await s.flush()
            m = ChatMessage(session_id=sess.id, role="assistant", content="ans",
                            citations=json.dumps({"citations": [{"entity_id": entity_id, "name": "x", "wiki": None}],
                                                  "bridge": []}),
                            rating=rating)
            s.add(m); await s.commit()
    run_async(_inner())


def _seed_two_ranked():
    """B strictly closer to the query vector than A -> baseline ranks B first."""
    async def _inner():
        async with async_session_maker() as s:
            src = Source(title="fb-src", filename="f.txt", file_path="p/f.txt", file_type="txt",
                         content_hash="h-fb", file_size=1, status="completed")
            s.add(src); await s.flush()
            a = Entity(name="EntityA", entity_type="concept", salience=0.0)
            b = Entity(name="EntityB", entity_type="concept", salience=0.0)
            s.add_all([a, b]); await s.flush()
            va = [0.0] * DIM; va[0] = 0.9; va[1] = 0.4359  # ~unit, angled away
            ca = Chunk(source_id=src.id, chunk_index=0, content="a", token_count=1,
                       doc_char_start=0, doc_char_end=1, embedding=va)
            cb = Chunk(source_id=src.id, chunk_index=1, content="b", token_count=1,
                       doc_char_start=0, doc_char_end=1, embedding=_vec(0))
            s.add_all([ca, cb]); await s.flush()
            s.add(EntityMention(entity_id=a.id, chunk_id=ca.id))
            s.add(EntityMention(entity_id=b.id, chunk_id=cb.id))
            await s.commit()
            return a.id, b.id
    return run_async(_inner())


def test_feedback_scores_extracted_from_rated_citations():
    a_id, _ = _seed_two_ranked()
    _rate_citing(a_id, 1)
    _rate_citing(a_id, 1)
    _rate_citing(a_id, -1)
    svc = RetrievalService(get_settings())
    net = run_async(svc._feedback_scores([a_id]))
    assert net == {a_id: 1}  # 1 + 1 - 1


def test_feedback_factor_bounded():
    f = RetrievalService._feedback_factor
    assert f(0) == 1.0
    assert f(1) > 1.0 and f(-1) < 1.0
    assert f(100) == f(3)      # clamped
    assert f(-100) == f(-3)
    assert 0.5 < f(-100) and f(100) < 1.5  # bounded, never zeroing


def test_thumbs_up_flips_close_ranking():
    a_id, b_id = _seed_two_ranked()
    svc = RetrievalService(get_settings(), llm_service=_FakeEmbedLLM())

    baseline = run_async(svc.search("anything", k=5))
    base_ids = [r["entity_id"] for r in baseline]
    assert base_ids.index(b_id) < base_ids.index(a_id), "precondition: B outranks A before feedback"

    _rate_citing(a_id, 1)
    boosted = run_async(svc.search("anything", k=5))
    new_ids = [r["entity_id"] for r in boosted]
    assert new_ids.index(a_id) < new_ids.index(b_id), "thumbs-up on A must flip the close ranking"


def test_ratings_on_merged_member_reach_canonical():
    """A rating that cited a pre-merge member id must boost the canonical after the merge."""
    async def _inner():
        async with async_session_maker() as s:
            root = Entity(name="Root", entity_type="concept")
            member = Entity(name="Member", entity_type="concept")
            s.add_all([root, member]); await s.flush()
            member.canonical_entity_id = root.id
            await s.commit()
            return root.id, member.id

    root_id, member_id = run_async(_inner())
    _rate_citing(member_id, 1)  # rated BEFORE/at merge time, citing the raw member id
    svc = RetrievalService(get_settings())
    net = run_async(svc._feedback_scores([root_id]))
    assert net == {root_id: 1}, "member's rating must resolve to its canonical root"
