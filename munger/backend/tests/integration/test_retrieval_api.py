"""GET /api/search/retrieve wiring: handler returns entity-centric results; route is registered."""

from app.api.retrieval import retrieve
from app.core.database import async_session_maker
from app.models.chunk import Chunk
from app.models.entity import Entity, EntityMention
from app.models.source import Source
from app.services import retrieval_service as rs
from tests.conftest import run_async

DIM = 768


def _vec(i):
    v = [0.0] * DIM
    v[i] = 1.0
    return v


def test_retrieve_handler_returns_results(monkeypatch):
    async def _setup():
        async with async_session_maker() as s:
            src = Source(title="api-src", filename="f.txt", file_path="p/f.txt", file_type="txt",
                         content_hash="h-api", file_size=1, status="completed")
            s.add(src); await s.flush()
            e = Entity(name="Alpha", entity_type="concept", salience=0.5)
            s.add(e); await s.flush()
            c = Chunk(source_id=src.id, chunk_index=0, content="alpha",
                      token_count=1, doc_char_start=0, doc_char_end=1, embedding=_vec(0))
            s.add(c); await s.flush()
            s.add(EntityMention(entity_id=e.id, chunk_id=c.id, context="alpha here"))
            await s.commit()
            return e.id

    e_id = run_async(_setup())

    async def _fake_embed(self, q):  # avoid any external LLM call
        return _vec(0)

    monkeypatch.setattr(rs.RetrievalService, "_embed_query", _fake_embed)

    body = run_async(retrieve(q="alpha", k=10))
    assert "results" in body and body["query"] == "alpha"
    assert any(r["entity_id"] == e_id for r in body["results"])


def test_retrieve_route_registered():
    from app.main import app
    paths = {getattr(r, "path", None) for r in app.routes}
    assert "/api/search/retrieve" in paths
