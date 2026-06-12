"""PgVectorStore: VectorStore interface over the chunks/entities embedding columns."""

import pytest

from app.core.config import get_settings
from app.core.database import async_session_maker
from app.models.chunk import Chunk
from app.services.vector_store import PgVectorStore, VectorHit, get_vector_store
from tests.conftest import run_async

DIM = 768


def _one_hot(pos: int) -> list[float]:
    vec = [0.0] * DIM
    vec[pos] = 1.0
    return vec


def _weighted(*pairs: tuple[int, float]) -> list[float]:
    vec = [0.0] * DIM
    for pos, value in pairs:
        vec[pos] = value
    return vec


async def _seed_chunks(source_id: int, count: int) -> list[int]:
    async with async_session_maker() as session:
        chunks = []
        for i in range(count):
            chunk = Chunk(
                source_id=source_id,
                chunk_index=i,
                content=f"chunk {i}",
                token_count=2,
                doc_char_start=0,
                doc_char_end=8,
            )
            session.add(chunk)
            chunks.append(chunk)
        await session.commit()
        return [c.id for c in chunks]


def test_upsert_and_search_chunks_orders_by_distance(create_source):
    source = create_source(title="VS chunks", status="completed")

    async def _go():
        ids = await _seed_chunks(source.id, 3)
        store = PgVectorStore()
        await store.upsert_chunks([(ids[i], source.id, _one_hot(i)) for i in range(3)])
        # query weight decreases across positions 0,1,2 -> strict distance ordering
        hits = await store.search_chunks(
            _weighted((0, 0.7), (1, 0.5), (2, 0.1)), limit=10
        )
        exact = await store.search_chunks(_one_hot(0), limit=1)
        return ids, hits, exact

    ids, hits, exact = run_async(_go())
    assert isinstance(hits[0], VectorHit)
    assert [h.id for h in hits] == ids
    assert hits[0].distance < hits[1].distance < hits[2].distance
    assert exact[0].id == ids[0]
    assert exact[0].distance == pytest.approx(0.0, abs=1e-6)


def test_search_chunks_source_filter_excludes_other_sources(create_source):
    s1 = create_source(title="VS filter src1", status="completed")
    s2 = create_source(title="VS filter src2", status="completed")

    async def _go():
        (c1,) = await _seed_chunks(s1.id, 1)
        (c2,) = await _seed_chunks(s2.id, 1)
        store = PgVectorStore()
        await store.upsert_chunks([(c1, s1.id, _one_hot(0)), (c2, s2.id, _one_hot(0))])
        filtered = await store.search_chunks(_one_hot(0), limit=10, source_id=s1.id)
        unfiltered = await store.search_chunks(_one_hot(0), limit=10)
        return c1, c2, filtered, unfiltered

    c1, c2, filtered, unfiltered = run_async(_go())
    assert [h.id for h in filtered] == [c1]
    assert {h.id for h in unfiltered} == {c1, c2}


def test_upsert_and_search_entities(create_entity):
    e0 = create_entity(name="VS-E0")
    e1 = create_entity(name="VS-E1")
    e2 = create_entity(name="VS-E2")

    async def _go():
        store = PgVectorStore()
        await store.upsert_entities(
            [(e0.id, _one_hot(0)), (e1.id, _one_hot(1)), (e2.id, _one_hot(2))]
        )
        return await store.search_entities(
            _weighted((0, 0.7), (1, 0.5), (2, 0.1)), limit=10
        )

    hits = run_async(_go())
    assert [h.id for h in hits] == [e0.id, e1.id, e2.id]
    assert hits[0].distance < hits[1].distance < hits[2].distance


def test_get_entity_vectors_roundtrips_exact_vectors(create_entity):
    e0 = create_entity(name="VS-RT0")
    e1 = create_entity(name="VS-RT1")
    bare = create_entity(name="VS-RT-bare")  # never embedded

    vec0 = _weighted((0, 0.5), (3, 0.25))
    vec1 = _weighted((1, 0.125), (5, 0.75))

    async def _go():
        store = PgVectorStore()
        await store.upsert_entities([(e0.id, vec0), (e1.id, vec1)])
        return await store.get_entity_vectors([e0.id, e1.id, bare.id])

    vectors = run_async(_go())
    assert set(vectors) == {e0.id, e1.id}
    assert vectors[e0.id] == pytest.approx(vec0)
    assert vectors[e1.id] == pytest.approx(vec1)
    assert all(isinstance(x, float) for x in vectors[e0.id])


def test_reupsert_overwrites_vector(create_source):
    source = create_source(title="VS overwrite", status="completed")

    async def _go():
        (cid,) = await _seed_chunks(source.id, 1)
        store = PgVectorStore()
        await store.upsert_chunks([(cid, source.id, _one_hot(0))])
        before = await store.search_chunks(_one_hot(0), limit=10)
        await store.upsert_chunks([(cid, source.id, _one_hot(1))])
        after = await store.search_chunks(_one_hot(0), limit=10)
        return cid, before, after

    cid, before, after = run_async(_go())
    assert [h.id for h in before] == [cid]
    assert before[0].distance == pytest.approx(0.0, abs=1e-6)
    assert [h.id for h in after] == [cid]
    assert after[0].distance == pytest.approx(1.0, abs=1e-6)


def test_empty_inputs_are_noops():
    async def _go():
        store = PgVectorStore()
        await store.upsert_chunks([])
        await store.upsert_entities([])
        vectors = await store.get_entity_vectors([])
        await store.delete_entities([])
        await store.delete_chunks_for_source(123456)
        await store.delete_entities([1, 2, 3])
        hits = await store.search_chunks(_one_hot(0), limit=5)
        return vectors, hits

    vectors, hits = run_async(_go())
    assert vectors == {}
    assert hits == []


def test_get_vector_store_factory():
    store = get_vector_store()
    assert isinstance(store, PgVectorStore)
    assert store.backend == "pgvector"

    settings = get_settings()
    with pytest.raises(ValueError):
        get_vector_store(settings.model_copy(update={"vector_backend": "duckdb"}))
    lance = get_vector_store(settings.model_copy(update={"vector_backend": "lancedb"}))
    assert lance.backend == "lancedb"
