"""Vector store abstraction (SP1.2): pgvector in Postgres today, LanceDB behind a flag.

Selected via ``VECTOR_BACKEND``. The pgvector backend reads/writes the existing
``chunks.embedding`` / ``entities.embedding`` columns, so it is a thin adapter
over SQL the services already run today.
"""

from __future__ import annotations

import abc
from typing import NamedTuple, Sequence

from sqlalchemy import select, text, update

from app.core.config import Settings, get_settings
from app.core.database import async_session_maker
from app.models.chunk import Chunk
from app.models.entity import Entity


class VectorHit(NamedTuple):
    id: int
    distance: float


class VectorStore(abc.ABC):
    """Backend-agnostic vector index over chunk and entity embeddings."""

    backend: str

    @abc.abstractmethod
    async def upsert_chunks(self, items: Sequence[tuple[int, int, list[float]]]) -> None:
        """Upsert ``(chunk_id, source_id, vector)`` triples."""

    @abc.abstractmethod
    async def upsert_entities(self, items: Sequence[tuple[int, list[float]]]) -> None:
        """Upsert ``(entity_id, vector)`` pairs."""

    @abc.abstractmethod
    async def search_chunks(
        self, vec: list[float], *, limit: int, source_id: int | None = None
    ) -> list[VectorHit]:
        """Nearest chunks by cosine distance, optionally restricted to one source."""

    @abc.abstractmethod
    async def search_entities(self, vec: list[float], *, limit: int) -> list[VectorHit]:
        """Nearest entities by cosine distance."""

    @abc.abstractmethod
    async def get_entity_vectors(self, ids: Sequence[int]) -> dict[int, list[float]]:
        """Stored vectors for *ids*; ids without a vector are omitted."""

    @abc.abstractmethod
    async def delete_chunks_for_source(self, source_id: int) -> None:
        """Drop all chunk vectors belonging to *source_id*."""

    @abc.abstractmethod
    async def delete_entities(self, ids: Sequence[int]) -> None:
        """Drop entity vectors for *ids*."""


def _vec_literal(vec: list[float]) -> str:
    return "[" + ",".join(str(float(x)) for x in vec) + "]"


class PgVectorStore(VectorStore):
    """Vectors live in the pgvector ``embedding`` columns of chunks/entities."""

    backend = "pgvector"

    async def upsert_chunks(self, items: Sequence[tuple[int, int, list[float]]]) -> None:
        if not items:
            return
        async with async_session_maker() as session:
            for chunk_id, _source_id, vector in items:
                await session.execute(
                    update(Chunk).where(Chunk.id == chunk_id).values(embedding=vector)
                )
            await session.commit()

    async def upsert_entities(self, items: Sequence[tuple[int, list[float]]]) -> None:
        if not items:
            return
        async with async_session_maker() as session:
            for entity_id, vector in items:
                await session.execute(
                    update(Entity).where(Entity.id == entity_id).values(embedding=vector)
                )
            await session.commit()

    async def search_chunks(
        self, vec: list[float], *, limit: int, source_id: int | None = None
    ) -> list[VectorHit]:
        if not vec:
            return []
        sql = (
            "SELECT id, (embedding <=> CAST(:vec AS vector)) AS d "
            "FROM chunks WHERE embedding IS NOT NULL"
        )
        params: dict = {"vec": _vec_literal(vec), "lim": limit}
        if source_id is not None:
            sql += " AND source_id = :src"
            params["src"] = source_id
        sql += " ORDER BY d LIMIT :lim"
        async with async_session_maker() as session:
            rows = (await session.execute(text(sql), params)).all()
        return [VectorHit(id=r[0], distance=float(r[1])) for r in rows]

    async def search_entities(self, vec: list[float], *, limit: int) -> list[VectorHit]:
        if not vec:
            return []
        async with async_session_maker() as session:
            rows = (
                await session.execute(
                    text(
                        "SELECT id, (embedding <=> CAST(:vec AS vector)) AS d "
                        "FROM entities WHERE embedding IS NOT NULL "
                        "ORDER BY d LIMIT :lim"
                    ),
                    {"vec": _vec_literal(vec), "lim": limit},
                )
            ).all()
        return [VectorHit(id=r[0], distance=float(r[1])) for r in rows]

    async def get_entity_vectors(self, ids: Sequence[int]) -> dict[int, list[float]]:
        if not ids:
            return {}
        async with async_session_maker() as session:
            rows = (
                await session.execute(
                    select(Entity.id, Entity.embedding).where(
                        Entity.id.in_(list(ids)), Entity.embedding.is_not(None)
                    )
                )
            ).all()
        return {row[0]: [float(x) for x in row[1]] for row in rows}

    async def delete_chunks_for_source(self, source_id: int) -> None:
        """No-op: the chunks row lifecycle owns the pg embedding column."""
        return None

    async def delete_entities(self, ids: Sequence[int]) -> None:
        """No-op: the entities row lifecycle owns the pg embedding column."""
        return None


def get_vector_store(settings: Settings | None = None) -> VectorStore:
    """Resolve the configured backend (``VECTOR_BACKEND``) to a VectorStore."""
    cfg = settings or get_settings()
    backend = cfg.vector_backend
    if backend == "pgvector":
        return PgVectorStore()
    if backend == "lancedb":
        from app.services.lancedb_store import get_lancedb_store

        return get_lancedb_store(cfg.lancedb_uri, cfg.embedding_dimensions)
    raise ValueError(
        f"Unknown VECTOR_BACKEND={backend!r} (expected 'pgvector' or 'lancedb')"
    )
