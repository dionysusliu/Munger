"""LanceDB vector store (SP1.2): embedded ANN dataset behind the VectorStore seam.

Single-writer model: the ingest worker is the only process that writes these
tables; API readers share the same dataset directory safely (LanceDB MVCC).
Connections and table handles open lazily on first use and are cached, so
constructing the store (e.g. from ``get_vector_store``) never touches disk.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Sequence

import pyarrow as pa

from app.services.vector_store import VectorHit, VectorStore

if TYPE_CHECKING:
    from lancedb import AsyncConnection
    from lancedb.table import AsyncTable

CHUNK_TABLE = "chunk_vectors"
ENTITY_TABLE = "entity_vectors"


def _id_list(ids: Sequence[int]) -> str:
    return ", ".join(str(int(i)) for i in ids)


class LanceDBStore(VectorStore):
    """Vectors live in LanceDB tables under ``LANCEDB_URI``."""

    backend = "lancedb"

    def __init__(self, uri: str, dim: int) -> None:
        self.uri = uri
        self.dim = dim
        self._db: AsyncConnection | None = None
        self._tables: dict[str, AsyncTable] = {}

    def _schema(self, table: str) -> pa.Schema:
        fields = [pa.field("id", pa.int64())]
        if table == CHUNK_TABLE:
            fields.append(pa.field("source_id", pa.int64()))
        fields.append(pa.field("vector", pa.list_(pa.float32(), self.dim)))
        return pa.schema(fields)

    async def _connect(self) -> AsyncConnection:
        if self._db is None:
            from datetime import timedelta

            import lancedb

            # interval 0: every read checks for the latest committed version, so
            # API readers immediately see worker (or migration-tool) writes
            self._db = await lancedb.connect_async(
                self.uri, read_consistency_interval=timedelta(seconds=0)
            )
        return self._db

    async def _table(self, name: str) -> AsyncTable:
        """Open *name* for writing, creating it on first use."""
        tbl = self._tables.get(name)
        if tbl is None:
            db = await self._connect()
            tbl = await db.create_table(name, schema=self._schema(name), exist_ok=True)
            self._tables[name] = tbl
        return tbl

    async def _existing_table(self, name: str) -> AsyncTable | None:
        """Open *name* if it exists; readers and deleters never create tables."""
        tbl = self._tables.get(name)
        if tbl is None:
            db = await self._connect()
            try:
                tbl = await db.open_table(name)
            except ValueError:
                return None
            self._tables[name] = tbl
        return tbl

    async def _merge(self, name: str, rows: list[dict]) -> None:
        tbl = await self._table(name)
        await (
            tbl.merge_insert("id")
            .when_matched_update_all()
            .when_not_matched_insert_all()
            .execute(rows)
        )

    async def upsert_chunks(self, items: Sequence[tuple[int, int, list[float]]]) -> None:
        if not items:
            return
        await self._merge(
            CHUNK_TABLE,
            [
                {
                    "id": int(chunk_id),
                    "source_id": int(source_id),
                    "vector": [float(x) for x in vector],
                }
                for chunk_id, source_id, vector in items
            ],
        )

    async def upsert_entities(self, items: Sequence[tuple[int, list[float]]]) -> None:
        if not items:
            return
        await self._merge(
            ENTITY_TABLE,
            [
                {"id": int(entity_id), "vector": [float(x) for x in vector]}
                for entity_id, vector in items
            ],
        )

    async def search_chunks(
        self, vec: list[float], *, limit: int, source_id: int | None = None
    ) -> list[VectorHit]:
        if not vec:
            return []
        tbl = await self._existing_table(CHUNK_TABLE)
        if tbl is None:
            return []
        query = tbl.query().nearest_to([float(x) for x in vec]).distance_type("cosine")
        if source_id is not None:
            query = query.where(f"source_id = {int(source_id)}")
        rows = await query.limit(limit).to_list()
        return [VectorHit(id=int(r["id"]), distance=float(r["_distance"])) for r in rows]

    async def search_entities(self, vec: list[float], *, limit: int) -> list[VectorHit]:
        if not vec:
            return []
        tbl = await self._existing_table(ENTITY_TABLE)
        if tbl is None:
            return []
        rows = await (
            tbl.query()
            .nearest_to([float(x) for x in vec])
            .distance_type("cosine")
            .limit(limit)
            .to_list()
        )
        return [VectorHit(id=int(r["id"]), distance=float(r["_distance"])) for r in rows]

    async def get_entity_vectors(self, ids: Sequence[int]) -> dict[int, list[float]]:
        if not ids:
            return {}
        tbl = await self._existing_table(ENTITY_TABLE)
        if tbl is None:
            return {}
        rows = await (
            tbl.query().where(f"id IN ({_id_list(ids)})").select(["id", "vector"]).to_list()
        )
        return {int(r["id"]): [float(x) for x in r["vector"]] for r in rows}

    async def delete_chunks_for_source(self, source_id: int) -> None:
        tbl = await self._existing_table(CHUNK_TABLE)
        if tbl is None:
            return
        await tbl.delete(f"source_id = {int(source_id)}")

    async def delete_entities(self, ids: Sequence[int]) -> None:
        if not ids:
            return
        tbl = await self._existing_table(ENTITY_TABLE)
        if tbl is None:
            return
        await tbl.delete(f"id IN ({_id_list(ids)})")


_STORES: dict[tuple[str, int], LanceDBStore] = {}


def get_lancedb_store(uri: str, dim: int) -> LanceDBStore:
    """Shared store per (uri, dim) so all callers reuse one lazy connection."""
    key = (uri, dim)
    store = _STORES.get(key)
    if store is None:
        store = _STORES[key] = LanceDBStore(uri, dim)
    return store
