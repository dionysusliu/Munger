"""RetrievalService recall channels: vector (chunk-ANN->mentions), lexical (wiki-FTS), graph (PPR)."""

from sqlalchemy import text

from app.core.config import get_settings
from app.core.database import async_session_maker
from app.models.chunk import Chunk
from app.models.entity import Entity, EntityMention
from app.models.entity_edge import EntityEdge
from app.models.source import Source
from app.models.wiki import WikiPage
from app.services.retrieval_service import RetrievalService
from tests.conftest import run_async

DIM = 768


def _vec(i: int) -> list[float]:
    v = [0.0] * DIM
    v[i] = 1.0
    return v


class _FakeEmbedLLM:
    async def embed_text(self, text_in: str) -> list[float]:
        return _vec(0) if "alpha" in text_in.lower() else _vec(1)


def _svc():
    return RetrievalService(get_settings(), llm_service=_FakeEmbedLLM())


def _make_source(s):
    src = Source(title="ret-src", filename="f.txt", file_path="p/f.txt", file_type="txt",
                 content_hash="h-ret", file_size=1, status="completed")
    s.add(src)
    return src


def _chunk(src_id, idx, content, embedding):
    return Chunk(source_id=src_id, chunk_index=idx, content=content,
                 token_count=1, doc_char_start=0, doc_char_end=1, embedding=embedding)


def test_vector_channel_maps_chunks_to_entities():
    async def _setup():
        async with async_session_maker() as s:
            src = _make_source(s); await s.flush()
            ea = Entity(name="Alpha", entity_type="concept")
            eb = Entity(name="Beta", entity_type="concept")
            s.add(ea); s.add(eb); await s.flush()
            ca = _chunk(src.id, 0, "a", _vec(0))
            cb = _chunk(src.id, 1, "b", _vec(1))
            s.add(ca); s.add(cb); await s.flush()
            s.add(EntityMention(entity_id=ea.id, chunk_id=ca.id))
            s.add(EntityMention(entity_id=eb.id, chunk_id=cb.id))
            await s.commit()
            return ea.id, eb.id

    a_id, b_id = run_async(_setup())
    qvec = _vec(0)
    ranked = run_async(_svc()._vector_entities(qvec, limit=10))
    assert ranked and ranked[0] == a_id
    assert b_id in ranked


def test_lexical_channel_maps_wiki_fts_to_entities():
    async def _setup():
        async with async_session_maker() as s:
            ea = Entity(name="Photosynthesis", entity_type="concept")
            s.add(ea); await s.flush()
            wp = WikiPage(slug="photosynthesis", title="Photosynthesis",
                          content="Photosynthesis converts light into chemical energy.")
            s.add(wp); await s.flush()
            ea.wiki_page_id = wp.id
            await s.execute(text(
                "UPDATE wiki_pages SET search_vector = to_tsvector('english', content) WHERE id = :i"),
                {"i": wp.id})
            await s.commit()
            return ea.id

    a_id = run_async(_setup())
    ranked = run_async(_svc()._lexical_entities("photosynthesis light", limit=10))
    assert a_id in ranked


def test_graph_channel_pulls_seed_neighbors():
    async def _setup():
        async with async_session_maker() as s:
            ents = [Entity(name=n, entity_type="concept") for n in ["S", "N", "Far"]]
            for e in ents:
                s.add(e)
            await s.flush()
            sid, nid, fid = [e.id for e in ents]
            lo, hi = (sid, nid) if sid < nid else (nid, sid)
            s.add(EntityEdge(src_entity_id=lo, tgt_entity_id=hi, weight=5.0, evidence_count=1))
            await s.commit()
            return sid, nid, fid

    sid, nid, fid = run_async(_setup())
    ranked = run_async(_svc()._graph_entities([sid], limit=10))
    assert sid in ranked and nid in ranked
    assert ranked.index(nid) < ranked.index(fid) if fid in ranked else True


def test_link_seeds_exact_and_ilike():
    async def _setup():
        async with async_session_maker() as s:
            for n in ["Compound Interest", "Latticework"]:
                s.add(Entity(name=n, entity_type="concept"))
            await s.commit()

    run_async(_setup())
    seeds = run_async(_svc().link_seeds("compound interest"))
    async def _name(eid):
        async with async_session_maker() as s:
            return (await s.execute(text("SELECT name FROM entities WHERE id=:i"), {"i": eid})).scalar()
    names = [run_async(_name(e)) for e in seeds]
    assert "Compound Interest" in names
