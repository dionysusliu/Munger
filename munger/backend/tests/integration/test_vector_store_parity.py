"""Backend parity: PgVectorStore and LanceDBStore rank the same data identically.

Shared dataset per backend: chunks c0,c1 in source A and c2 in source B with
one-hot vectors at positions 0/1/2; entities e0..e2 one-hot at 0/1/2. Orders are
compared via seed index (pg ids are autoincrement, lance ids are fixed ints).
"""

import pytest
from sqlalchemy import func, select, update

from app.core.database import async_session_maker
from app.models.chunk import Chunk
from app.models.entity import Entity
from app.models.source import Source
from app.services.lancedb_store import LanceDBStore
from app.services.vector_store import PgVectorStore
from scripts.migrate_vectors import migrate
from tests.conftest import run_async

DIM = 768

BACKENDS = ["pgvector", "lancedb"]


def _one_hot(pos: int) -> list[float]:
    vec = [0.0] * DIM
    vec[pos] = 1.0
    return vec


def _weighted(*pairs: tuple[int, float]) -> list[float]:
    vec = [0.0] * DIM
    for pos, value in pairs:
        vec[pos] = value
    return vec


# weights strictly decrease across positions 0,1,2 -> expected order [0, 1, 2]
QUERY_A = _weighted((0, 0.7), (1, 0.5), (2, 0.1))
# distinct weights, different winner -> expected order [1, 2, 0]
QUERY_B = _weighted((0, 0.1), (1, 0.9), (2, 0.3))


async def _seed_pg() -> tuple[list[int], list[int], tuple[int, int]]:
    async with async_session_maker() as session:
        s1 = Source(title="parity-s1", filename="f.txt", file_path="p/f.txt",
                    file_type="txt", content_hash="h-parity-1", file_size=1,
                    status="completed")
        s2 = Source(title="parity-s2", filename="g.txt", file_path="p/g.txt",
                    file_type="txt", content_hash="h-parity-2", file_size=1,
                    status="completed")
        session.add(s1)
        session.add(s2)
        await session.flush()
        chunks = []
        for i, src in enumerate([s1, s1, s2]):
            chunk = Chunk(source_id=src.id, chunk_index=i, content=f"parity chunk {i}",
                          token_count=2, doc_char_start=0, doc_char_end=8)
            session.add(chunk)
            chunks.append(chunk)
        entities = [Entity(name=f"Parity-E{i}", entity_type="concept") for i in range(3)]
        for entity in entities:
            session.add(entity)
        await session.commit()
        return [c.id for c in chunks], [e.id for e in entities], (s1.id, s2.id)


def _make_backend(backend: str, tmp_path):
    if backend == "pgvector":
        chunk_ids, entity_ids, source_ids = run_async(_seed_pg())
        store = PgVectorStore()
    else:
        store = LanceDBStore(str(tmp_path / f"lance-{backend}"), DIM)
        chunk_ids, entity_ids, source_ids = [11, 12, 13], [21, 22, 23], (1, 2)
    run_async(store.upsert_chunks([
        (chunk_ids[0], source_ids[0], _one_hot(0)),
        (chunk_ids[1], source_ids[0], _one_hot(1)),
        (chunk_ids[2], source_ids[1], _one_hot(2)),
    ]))
    run_async(store.upsert_entities([(entity_ids[i], _one_hot(i)) for i in range(3)]))
    return store, chunk_ids, entity_ids, source_ids


def _run_queries(store, chunk_ids, entity_ids, source_ids):
    """Same query set against any backend, with ids normalized to seed index."""

    async def _go():
        return {
            "chunks_a": await store.search_chunks(QUERY_A, limit=10),
            "chunks_b": await store.search_chunks(QUERY_B, limit=10),
            "chunks_a_src": await store.search_chunks(
                QUERY_A, limit=10, source_id=source_ids[0]
            ),
            "chunks_b_src": await store.search_chunks(
                QUERY_B, limit=10, source_id=source_ids[0]
            ),
            "entities_a": await store.search_entities(QUERY_A, limit=10),
            "entities_b": await store.search_entities(QUERY_B, limit=10),
        }

    hits = run_async(_go())
    index = {cid: i for i, cid in enumerate(chunk_ids)}
    index.update({eid: i for i, eid in enumerate(entity_ids)})
    orders = {key: [index[h.id] for h in value] for key, value in hits.items()}
    distances = {key: [h.distance for h in value] for key, value in hits.items()}
    return orders, distances


@pytest.mark.parametrize("backend", BACKENDS)
def test_backend_ranks_shared_dataset(backend, tmp_path):
    store, chunk_ids, entity_ids, source_ids = _make_backend(backend, tmp_path)
    orders, distances = _run_queries(store, chunk_ids, entity_ids, source_ids)

    assert orders["chunks_a"] == [0, 1, 2]
    assert orders["chunks_b"] == [1, 2, 0]
    assert orders["chunks_a_src"] == [0, 1]
    assert orders["chunks_b_src"] == [1, 0]
    assert orders["entities_a"] == [0, 1, 2]
    assert orders["entities_b"] == [1, 2, 0]
    for values in distances.values():
        assert values == sorted(values)  # monotone nondecreasing


def test_backends_rank_identically(tmp_path):
    results = {}
    for backend in BACKENDS:
        store, chunk_ids, entity_ids, source_ids = _make_backend(backend, tmp_path)
        orders, _ = _run_queries(store, chunk_ids, entity_ids, source_ids)
        results[backend] = orders
    assert results["pgvector"] == results["lancedb"]


def test_migrate_pgvector_to_lancedb_roundtrip(tmp_path):
    chunk_ids, entity_ids, source_ids = run_async(_seed_pg())
    pg = PgVectorStore()
    run_async(pg.upsert_chunks([
        (chunk_ids[0], source_ids[0], _one_hot(0)),
        (chunk_ids[1], source_ids[0], _one_hot(1)),
        (chunk_ids[2], source_ids[1], _one_hot(2)),
    ]))
    run_async(pg.upsert_entities([(entity_ids[i], _one_hot(i)) for i in range(3)]))

    uri = str(tmp_path / "lance-migrated")
    counts = run_async(migrate("lancedb", lancedb_uri=uri))
    assert counts == {"chunks": 3, "entities": 3}

    lance = LanceDBStore(uri, DIM)
    chunk_hits = run_async(lance.search_chunks(QUERY_A, limit=10))
    assert {h.id for h in chunk_hits} == set(chunk_ids)
    entity_hits = run_async(lance.search_entities(QUERY_A, limit=10))
    assert {h.id for h in entity_hits} == set(entity_ids)

    # idempotent: second run converges to the same totals, no duplicate rows
    counts_again = run_async(migrate("lancedb", lancedb_uri=uri))
    assert counts_again == counts
    assert [h.id for h in run_async(lance.search_chunks(QUERY_A, limit=10))] == [
        h.id for h in chunk_hits
    ]

    # --prune drops lance rows whose pg row was deleted
    async def _drop_last_chunk():
        async with async_session_maker() as session:
            chunk = await session.get(Chunk, chunk_ids[2])
            await session.delete(chunk)
            await session.commit()

    run_async(_drop_last_chunk())
    pruned = run_async(migrate("lancedb", lancedb_uri=uri, prune=True))
    assert pruned["pruned_chunks"] == 1
    assert pruned["pruned_entities"] == 0
    assert {h.id for h in run_async(lance.search_chunks(QUERY_A, limit=10))} == set(
        chunk_ids[:2]
    )

    # reverse direction restores the pg columns after they are nulled out
    async def _null_pg_embeddings():
        async with async_session_maker() as session:
            await session.execute(update(Chunk).values(embedding=None))
            await session.execute(update(Entity).values(embedding=None))
            await session.commit()

    async def _pg_embedded_counts():
        async with async_session_maker() as session:
            chunks = (await session.execute(
                select(func.count()).select_from(Chunk).where(Chunk.embedding.is_not(None))
            )).scalar()
            entities = (await session.execute(
                select(func.count()).select_from(Entity).where(Entity.embedding.is_not(None))
            )).scalar()
        return int(chunks), int(entities)

    run_async(_null_pg_embeddings())
    restored = run_async(migrate("pgvector", lancedb_uri=uri))
    assert restored == {"chunks": 2, "entities": 3}
    assert run_async(_pg_embedded_counts()) == (2, 3)
    assert run_async(pg.get_entity_vectors(entity_ids))[entity_ids[0]] == pytest.approx(
        _one_hot(0)
    )
