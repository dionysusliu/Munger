"""LanceDBStore: pgvector test matrix against a tmp-dir dataset (no Postgres rows)."""

import pytest

from app.core.config import get_settings
from app.services.lancedb_store import LanceDBStore, get_lancedb_store
from app.services.vector_store import VectorHit, get_vector_store
from tests.conftest import run_async

DIM = 8


def _one_hot(pos: int) -> list[float]:
    vec = [0.0] * DIM
    vec[pos] = 1.0
    return vec


def _weighted(*pairs: tuple[int, float]) -> list[float]:
    vec = [0.0] * DIM
    for pos, value in pairs:
        vec[pos] = value
    return vec


def _store(tmp_path) -> LanceDBStore:
    return LanceDBStore(str(tmp_path / "lance"), DIM)


def test_upsert_and_search_chunks_orders_by_distance(tmp_path):
    store = _store(tmp_path)

    async def _go():
        await store.upsert_chunks([(i + 1, 10, _one_hot(i)) for i in range(3)])
        # query weight decreases across positions 0,1,2 -> strict distance ordering
        hits = await store.search_chunks(
            _weighted((0, 0.7), (1, 0.5), (2, 0.1)), limit=10
        )
        exact = await store.search_chunks(_one_hot(0), limit=1)
        return hits, exact

    hits, exact = run_async(_go())
    assert isinstance(hits[0], VectorHit)
    assert [h.id for h in hits] == [1, 2, 3]
    assert hits[0].distance < hits[1].distance < hits[2].distance
    assert exact[0].id == 1
    assert exact[0].distance == pytest.approx(0.0, abs=1e-6)


def test_search_chunks_source_filter_excludes_other_sources(tmp_path):
    store = _store(tmp_path)

    async def _go():
        await store.upsert_chunks([(1, 10, _one_hot(0)), (2, 20, _one_hot(0))])
        filtered = await store.search_chunks(_one_hot(0), limit=10, source_id=10)
        unfiltered = await store.search_chunks(_one_hot(0), limit=10)
        return filtered, unfiltered

    filtered, unfiltered = run_async(_go())
    assert [h.id for h in filtered] == [1]
    assert {h.id for h in unfiltered} == {1, 2}


def test_upsert_and_search_entities(tmp_path):
    store = _store(tmp_path)

    async def _go():
        await store.upsert_entities(
            [(7, _one_hot(0)), (8, _one_hot(1)), (9, _one_hot(2))]
        )
        return await store.search_entities(
            _weighted((0, 0.7), (1, 0.5), (2, 0.1)), limit=10
        )

    hits = run_async(_go())
    assert [h.id for h in hits] == [7, 8, 9]
    assert hits[0].distance < hits[1].distance < hits[2].distance


def test_get_entity_vectors_roundtrips_exact_vectors(tmp_path):
    store = _store(tmp_path)
    vec0 = _weighted((0, 0.5), (3, 0.25))
    vec1 = _weighted((1, 0.125), (5, 0.75))

    async def _go():
        await store.upsert_entities([(1, vec0), (2, vec1)])
        return await store.get_entity_vectors([1, 2, 99])  # 99 never embedded

    vectors = run_async(_go())
    assert set(vectors) == {1, 2}
    assert vectors[1] == pytest.approx(vec0)
    assert vectors[2] == pytest.approx(vec1)
    assert all(isinstance(x, float) for x in vectors[1])


def test_reupsert_overwrites_vector(tmp_path):
    store = _store(tmp_path)

    async def _go():
        await store.upsert_chunks([(1, 10, _one_hot(0))])
        before = await store.search_chunks(_one_hot(0), limit=10)
        await store.upsert_chunks([(1, 10, _one_hot(1))])
        after = await store.search_chunks(_one_hot(0), limit=10)
        return before, after

    before, after = run_async(_go())
    assert [h.id for h in before] == [1]
    assert before[0].distance == pytest.approx(0.0, abs=1e-6)
    assert [h.id for h in after] == [1]  # merge_insert on id: no duplicate rows
    assert after[0].distance == pytest.approx(1.0, abs=1e-6)


def test_empty_inputs_and_missing_tables_are_noops(tmp_path):
    store = _store(tmp_path)

    async def _go():
        # empty upserts return before creating tables, so the calls below also
        # exercise the missing-table paths
        await store.upsert_chunks([])
        await store.upsert_entities([])
        vectors = await store.get_entity_vectors([])
        await store.delete_entities([])
        await store.delete_chunks_for_source(123456)
        await store.delete_entities([1, 2, 3])
        chunk_hits = await store.search_chunks(_one_hot(0), limit=5)
        entity_hits = await store.search_entities(_one_hot(0), limit=5)
        empty_query = await store.search_chunks([], limit=5)
        return vectors, chunk_hits, entity_hits, empty_query

    vectors, chunk_hits, entity_hits, empty_query = run_async(_go())
    assert vectors == {}
    assert chunk_hits == []
    assert entity_hits == []
    assert empty_query == []


def test_delete_chunks_for_source_removes_only_that_source(tmp_path):
    store = _store(tmp_path)

    async def _go():
        await store.upsert_chunks(
            [(1, 10, _one_hot(0)), (2, 10, _one_hot(1)), (3, 20, _one_hot(2))]
        )
        await store.delete_chunks_for_source(10)
        return await store.search_chunks(
            _weighted((0, 0.7), (1, 0.5), (2, 0.1)), limit=10
        )

    hits = run_async(_go())
    assert [h.id for h in hits] == [3]


def test_delete_entities_removes_listed_ids(tmp_path):
    store = _store(tmp_path)

    async def _go():
        await store.upsert_entities(
            [(1, _one_hot(0)), (2, _one_hot(1)), (3, _one_hot(2))]
        )
        await store.delete_entities([1, 3])
        hits = await store.search_entities(
            _weighted((0, 0.7), (1, 0.5), (2, 0.1)), limit=10
        )
        vectors = await store.get_entity_vectors([1, 2, 3])
        return hits, vectors

    hits, vectors = run_async(_go())
    assert [h.id for h in hits] == [2]
    assert set(vectors) == {2}


def test_get_lancedb_store_caches_per_uri_and_dim(tmp_path):
    a = get_lancedb_store(str(tmp_path / "x"), DIM)
    b = get_lancedb_store(str(tmp_path / "x"), DIM)
    c = get_lancedb_store(str(tmp_path / "y"), DIM)
    assert a is b
    assert a is not c
    assert a.backend == "lancedb"


def test_get_vector_store_resolves_lancedb_backend(tmp_path):
    settings = get_settings().model_copy(
        update={"vector_backend": "lancedb", "lancedb_uri": str(tmp_path / "lance")}
    )
    store = get_vector_store(settings)
    assert isinstance(store, LanceDBStore)
    assert store.uri == str(tmp_path / "lance")
    assert store.dim == settings.embedding_dimensions
