"""Helpers for per-chunk map lifecycle (pending → running → done | failed)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select, update

from app.core.config import Settings, get_settings
from app.core.database import async_session_maker
from app.models.chunk import Chunk

MAP_PENDING = "pending"
MAP_RUNNING = "running"
MAP_DONE = "done"
MAP_FAILED = "failed"

NEEDS_MAP = (MAP_PENDING, MAP_FAILED)


async def chunks_needing_map(source_id: int) -> list[int]:
    async with async_session_maker() as session:
        result = await session.execute(
            select(Chunk.id)
            .where(Chunk.source_id == source_id, Chunk.map_status.in_(NEEDS_MAP))
            .order_by(Chunk.chunk_index)
        )
        return list(result.scalars().all())


async def all_chunks_done(source_id: int) -> bool:
    async with async_session_maker() as session:
        result = await session.execute(
            select(func.count())
            .select_from(Chunk)
            .where(Chunk.source_id == source_id, Chunk.map_status != MAP_DONE)
        )
        return (result.scalar() or 0) == 0


async def reclaim_stale_running(source_id: int, settings: Settings | None = None) -> int:
    """Mark long-running map workers as failed so they can be retried."""
    settings = settings or get_settings()
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=settings.ingest_map_stale_minutes)
    async with async_session_maker() as session:
        result = await session.execute(
            update(Chunk)
            .where(
                Chunk.source_id == source_id,
                Chunk.map_status == MAP_RUNNING,
                Chunk.map_started_at.is_not(None),
                Chunk.map_started_at < cutoff,
            )
            .values(
                map_status=MAP_FAILED,
                map_last_error="Stale running map worker reclaimed",
            )
        )
        await session.commit()
        return result.rowcount or 0


async def claim_chunk_for_map(chunk_id: int) -> bool:
    """CAS pending|failed → running. Returns False if another worker claimed it."""
    async with async_session_maker() as session:
        result = await session.execute(
            update(Chunk)
            .where(Chunk.id == chunk_id, Chunk.map_status.in_(NEEDS_MAP))
            .values(
                map_status=MAP_RUNNING,
                map_attempts=Chunk.map_attempts + 1,
                map_started_at=datetime.now(timezone.utc),
                map_last_error=None,
            )
            .returning(Chunk.id)
        )
        claimed = result.scalar_one_or_none()
        await session.commit()
        return claimed is not None


async def mark_chunk_failed(chunk_id: int, error: str) -> None:
    async with async_session_maker() as session:
        await session.execute(
            update(Chunk)
            .where(Chunk.id == chunk_id)
            .values(map_status=MAP_FAILED, map_last_error=error[:2000])
        )
        await session.commit()
