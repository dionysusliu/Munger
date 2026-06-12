"""Injected VectorStore seam: ANN reads come from the store, not pgvector SQL.

Chunk/entity rows seeded here keep NULL pg embedding columns — only the in-test
fake holds vectors, so any vector hit proves the service queried the injected store.
"""

from sqlalchemy import text

from app.core.config import get_settings
from app.core.database import async_session_maker
from app.models.chunk import Chunk
from app.models.entity import Entity, EntityMention
from app.models.source import Source
from app.services.retrieval_service import _VECTOR_CHANNEL_POOL, RetrievalService
from app.services.search_service import SearchService
from app.services.vector_store import VectorHit, VectorStore
from tests.conftest import run_async

DIM = 8


def _vec(i: int) -> list[float]:
    v = [0.0] * DIM
    v[i] = 1.0
    return v


def _cos_dist(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    if na == 0 or nb == 0:
        return 1.0
    return 1.0 - dot / (na * nb)


class FakeVectorStore(VectorStore):
    backend = "fake"

    def __init__(self):
        self.chunk_vecs: dict[int, tuple[int, list[float]]] = {}
        self.entity_vecs: dict[int, list[float]] = {}
        self.chunk_search_limits: list[int] = []

    async def upsert_chunks(self, items):
        for chunk_id, source_id, vec in items:
            self.chunk_vecs[chunk_id] = (source_id, vec)

    async def upsert_entities(self, items):
        for entity_id, vec in items:
            self.entity_vecs[entity_id] = vec

    async def search_chunks(self, vec, *, limit, source_id=None):
        self.chunk_search_limits.append(limit)
        hits = [
            VectorHit(id=cid, distance=_cos_dist(vec, v))
            for cid, (sid, v) in self.chunk_vecs.items()
            if source_id is None or sid == source_id
        ]
        return sorted(hits, key=lambda h: h.distance)[:limit]

    async def search_entities(self, vec, *, limit):
        hits = [
            VectorHit(id=eid, distance=_cos_dist(vec, v))
            for eid, v in self.entity_vecs.items()
        ]
        return sorted(hits, key=lambda h: h.distance)[:limit]

    async def get_entity_vectors(self, ids):
        return {i: self.entity_vecs[i] for i in ids if i in self.entity_vecs}

    async def delete_chunks_for_source(self, source_id):
        self.chunk_vecs = {
            c: (s, v) for c, (s, v) in self.chunk_vecs.items() if s != source_id
        }

    async def delete_entities(self, ids):
        for i in ids:
            self.entity_vecs.pop(i, None)


class _FakeEmbedLLM:
    async def embed_text(self, q: str) -> list[float]:
        return _vec(0)


async def _pg_embedding_count() -> int:
    async with async_session_maker() as s:
        chunks = (await s.execute(
            text("SELECT COUNT(*) FROM chunks WHERE embedding IS NOT NULL"))).scalar()
        ents = (await s.execute(
            text("SELECT COUNT(*) FROM entities WHERE embedding IS NOT NULL"))).scalar()
    return int(chunks) + int(ents)


def test_semantic_search_reads_from_injected_store():
    async def _setup():
        async with async_session_maker() as s:
            src = Source(title="seam-src", filename="f.txt", file_path="p/f.txt",
                         file_type="txt", content_hash="h-seam-1", file_size=1,
                         status="completed")
            s.add(src); await s.flush()
            c0 = Chunk(source_id=src.id, chunk_index=0, content="chunk body 0",
                       token_count=1, doc_char_start=0, doc_char_end=1)
            c1 = Chunk(source_id=src.id, chunk_index=1, content="chunk body 1",
                       token_count=1, doc_char_start=1, doc_char_end=2)
            s.add(c0); s.add(c1); await s.commit()
            return src.id, c0.id, c1.id

    src_id, c0, c1 = run_async(_setup())
    fake = FakeVectorStore()
    run_async(fake.upsert_chunks([(c0, src_id, _vec(0)), (c1, src_id, _vec(1))]))

    svc = SearchService(llm_service=_FakeEmbedLLM(), vector_store=fake)
    results = run_async(svc.semantic_search("anything", limit=5))

    assert [r.chunk_id for r in results] == [c0, c1]
    assert all(r.result_type == "chunk" for r in results)
    assert results[0].score > results[1].score
    assert results[0].content == "chunk body 0"
    assert run_async(_pg_embedding_count()) == 0  # vectors never touched pg columns


def test_retrieval_channels_read_from_injected_store():
    async def _setup():
        async with async_session_maker() as s:
            src = Source(title="seam-ret", filename="f.txt", file_path="p/f.txt",
                         file_type="txt", content_hash="h-seam-2", file_size=1,
                         status="completed")
            s.add(src); await s.flush()
            ea = Entity(name="SeamAlpha", entity_type="concept")
            eb = Entity(name="SeamBeta", entity_type="concept")
            s.add(ea); s.add(eb); await s.flush()
            ca = Chunk(source_id=src.id, chunk_index=0, content="a",
                       token_count=1, doc_char_start=0, doc_char_end=1)
            cb = Chunk(source_id=src.id, chunk_index=1, content="b",
                       token_count=1, doc_char_start=1, doc_char_end=2)
            s.add(ca); s.add(cb); await s.flush()
            s.add(EntityMention(entity_id=ea.id, chunk_id=ca.id))
            s.add(EntityMention(entity_id=eb.id, chunk_id=cb.id))
            await s.commit()
            return src.id, ea.id, eb.id, ca.id, cb.id

    src_id, ea_id, eb_id, ca_id, cb_id = run_async(_setup())
    fake = FakeVectorStore()
    run_async(fake.upsert_chunks([(ca_id, src_id, _vec(0)), (cb_id, src_id, _vec(1))]))
    run_async(fake.upsert_entities([(ea_id, _vec(0)), (eb_id, _vec(1))]))

    svc = RetrievalService(get_settings(), llm_service=_FakeEmbedLLM(), vector_store=fake)

    ranked = run_async(svc._vector_entities(_vec(0), limit=10))
    assert ranked == [ea_id, eb_id]
    assert fake.chunk_search_limits == [_VECTOR_CHANNEL_POOL]

    seeds = run_async(svc.link_seeds("zzz", query_vec=_vec(0)))
    assert seeds[0] == ea_id
    assert eb_id in seeds

    results = run_async(svc.search("zzz", k=10))
    assert results and results[0]["entity_id"] == ea_id
    assert run_async(_pg_embedding_count()) == 0  # vectors never touched pg columns
