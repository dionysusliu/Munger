"""Retrieval is canonical-aware: merged duplicate entities surface as their canonical."""

from sqlalchemy import text

from app.core.config import get_settings
from app.core.database import async_session_maker
from app.models.chunk import Chunk
from app.models.entity import Entity, EntityMention
from app.models.source import Source
from app.services.retrieval_service import RetrievalService
from tests.conftest import run_async

DIM = 768


def _vec(i):
    v = [0.0] * DIM
    v[i] = 1.0
    return v


class _FakeEmbedLLM:
    async def embed_text(self, q):
        return _vec(0)


def _make_source(s):
    src = Source(title="rs", filename="f.txt", file_path="p/f.txt", file_type="txt",
                 content_hash="h-sp32", file_size=1, status="completed")
    s.add(src)
    return src


def test_link_seeds_resolves_to_canonical():
    async def _setup():
        async with async_session_maker() as s:
            a = Entity(name="Charlie Munger", entity_type="person", mention_count=9, salience=0.9)
            b = Entity(name="Charles Munger", entity_type="person", mention_count=2, salience=0.1)
            s.add(a); s.add(b); await s.flush()
            b.canonical_entity_id = a.id
            await s.commit()
            return a.id, b.id

    a_id, b_id = run_async(_setup())
    seeds = run_async(RetrievalService(get_settings()).link_seeds("charles munger"))
    assert a_id in seeds and b_id not in seeds


def test_search_collapses_duplicate_to_canonical():
    async def _setup():
        async with async_session_maker() as s:
            src = _make_source(s); await s.flush()
            a = Entity(name="Compound Interest", entity_type="concept", mention_count=9, salience=0.9)
            b = Entity(name="Compounding", entity_type="concept", mention_count=2, salience=0.1)
            s.add(a); s.add(b); await s.flush()
            b.canonical_entity_id = a.id
            ch = Chunk(source_id=src.id, chunk_index=0, content="c",
                       token_count=1, doc_char_start=0, doc_char_end=1, embedding=_vec(0))
            s.add(ch); await s.flush()
            s.add(EntityMention(entity_id=b.id, chunk_id=ch.id, context="compounding here"))
            await s.commit()
            return a.id, b.id

    a_id, b_id = run_async(_setup())
    results = run_async(RetrievalService(get_settings(), llm_service=_FakeEmbedLLM()).search("anything", k=10))
    ids = [r["entity_id"] for r in results]
    assert a_id in ids
    assert b_id not in ids
