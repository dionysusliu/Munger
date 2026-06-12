#!/usr/bin/env python3
"""Move vectors between the pgvector columns and the LanceDB dataset (SP1.2).

Usage:
    python scripts/migrate_vectors.py --to lancedb [--prune] [--batch 500]
    python scripts/migrate_vectors.py --to pgvector [--batch 500]

Idempotent: upserts converge, so a re-run reports the same totals. ``--prune``
(lancedb only) drops lance rows whose id no longer exists in Postgres.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import lancedb  # noqa: E402
from sqlalchemy import select, update  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.core.database import async_session_maker  # noqa: E402
from app.models.chunk import Chunk  # noqa: E402
from app.models.entity import Entity  # noqa: E402
from app.services.lancedb_store import CHUNK_TABLE, ENTITY_TABLE, LanceDBStore  # noqa: E402


async def _open_table(uri: str, name: str):
    db = await lancedb.connect_async(uri)
    try:
        return await db.open_table(name)
    except ValueError:
        return None


async def _to_lancedb(store: LanceDBStore, batch: int) -> dict[str, int]:
    counts = {"chunks": 0, "entities": 0}
    async with async_session_maker() as session:
        last_id = 0
        while True:
            rows = (
                await session.execute(
                    select(Chunk.id, Chunk.source_id, Chunk.embedding)
                    .where(Chunk.embedding.is_not(None), Chunk.id > last_id)
                    .order_by(Chunk.id)
                    .limit(batch)
                )
            ).all()
            if not rows:
                break
            await store.upsert_chunks(
                [(r[0], r[1], [float(x) for x in r[2]]) for r in rows]
            )
            counts["chunks"] += len(rows)
            last_id = rows[-1][0]

        last_id = 0
        while True:
            rows = (
                await session.execute(
                    select(Entity.id, Entity.embedding)
                    .where(Entity.embedding.is_not(None), Entity.id > last_id)
                    .order_by(Entity.id)
                    .limit(batch)
                )
            ).all()
            if not rows:
                break
            await store.upsert_entities(
                [(r[0], [float(x) for x in r[1]]) for r in rows]
            )
            counts["entities"] += len(rows)
            last_id = rows[-1][0]
    return counts


async def _to_pgvector(uri: str, batch: int) -> dict[str, int]:
    counts = {"chunks": 0, "entities": 0}
    for name, model, key in (
        (CHUNK_TABLE, Chunk, "chunks"),
        (ENTITY_TABLE, Entity, "entities"),
    ):
        tbl = await _open_table(uri, name)
        if tbl is None:
            continue
        reader = await (
            tbl.query().select(["id", "vector"]).to_batches(max_batch_length=batch)
        )
        async for record_batch in reader:
            rows = record_batch.to_pylist()
            if not rows:
                continue
            async with async_session_maker() as session:
                for row in rows:
                    await session.execute(
                        update(model)
                        .where(model.id == int(row["id"]))
                        .values(embedding=[float(x) for x in row["vector"]])
                    )
                await session.commit()
            counts[key] += len(rows)
    return counts


async def _prune_lancedb(uri: str) -> dict[str, int]:
    counts = {"pruned_chunks": 0, "pruned_entities": 0}
    async with async_session_maker() as session:
        pg_ids = {
            CHUNK_TABLE: set((await session.execute(select(Chunk.id))).scalars()),
            ENTITY_TABLE: set((await session.execute(select(Entity.id))).scalars()),
        }
    for name, key in (
        (CHUNK_TABLE, "pruned_chunks"),
        (ENTITY_TABLE, "pruned_entities"),
    ):
        tbl = await _open_table(uri, name)
        if tbl is None:
            continue
        lance_rows = await tbl.query().select(["id"]).to_list()
        stale = sorted({int(r["id"]) for r in lance_rows} - pg_ids[name])
        if stale:
            await tbl.delete(f"id IN ({', '.join(str(i) for i in stale)})")
        counts[key] = len(stale)
    return counts


async def migrate(
    to: str,
    *,
    lancedb_uri: str | None = None,
    batch: int = 500,
    prune: bool = False,
) -> dict[str, int]:
    settings = get_settings()
    uri = lancedb_uri or settings.lancedb_uri
    if to == "lancedb":
        store = LanceDBStore(uri, settings.embedding_dimensions)
        counts = await _to_lancedb(store, batch)
        if prune:
            counts.update(await _prune_lancedb(uri))
        return counts
    if to == "pgvector":
        return await _to_pgvector(uri, batch)
    raise ValueError(f"Unknown target {to!r} (expected 'lancedb' or 'pgvector')")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Move vectors between the pgvector columns and the LanceDB dataset"
    )
    parser.add_argument("--to", required=True, choices=("lancedb", "pgvector"))
    parser.add_argument(
        "--prune",
        action="store_true",
        help="lancedb only: drop lance rows whose id no longer exists in Postgres",
    )
    parser.add_argument("--batch", type=int, default=500)
    parser.add_argument("--lancedb-uri", default=None, help="override LANCEDB_URI")
    args = parser.parse_args(argv)
    if args.prune and args.to != "lancedb":
        parser.error("--prune only applies to --to lancedb")
    counts = asyncio.run(
        migrate(args.to, lancedb_uri=args.lancedb_uri, batch=args.batch, prune=args.prune)
    )
    for name, count in counts.items():
        print(f"{name}: {count}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
