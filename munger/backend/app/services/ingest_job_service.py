"""Ingest job queue operations."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.models.ingest_job import IngestJob

ACTIVE_STATUSES = ("pending", "claimed", "running")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def get_active_job(session: AsyncSession, source_id: int) -> IngestJob | None:
    result = await session.execute(
        select(IngestJob)
        .where(IngestJob.source_id == source_id, IngestJob.status.in_(ACTIVE_STATUSES))
        .order_by(IngestJob.id.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def enqueue_ingest_job(
    session: AsyncSession,
    source_id: int,
    *,
    skill_name: str = "ingest",
) -> IngestJob:
    existing = await get_active_job(session, source_id)
    if existing:
        return existing

    job = IngestJob(
        source_id=source_id,
        status="pending",
        skill_name=skill_name,
        heartbeat_at=_utcnow(),
    )
    session.add(job)
    try:
        await session.flush()
        await session.refresh(job)
        return job
    except IntegrityError:
        await session.rollback()
        existing = await get_active_job(session, source_id)
        if existing:
            return existing
        raise


async def claim_pending_jobs(
    session: AsyncSession,
    *,
    worker_id: str,
    limit: int,
) -> list[IngestJob]:
    result = await session.execute(
        select(IngestJob)
        .where(IngestJob.status == "pending")
        .order_by(IngestJob.created_at.asc())
        .limit(limit)
        .with_for_update(skip_locked=True)
    )
    jobs = list(result.scalars().all())
    now = _utcnow()
    for job in jobs:
        job.status = "claimed"
        job.claimed_by = worker_id
        job.heartbeat_at = now
        job.updated_at = now
    await session.flush()
    return jobs


async def mark_job_running(session: AsyncSession, job_id: int, thread_id: str) -> None:
    now = _utcnow()
    await session.execute(
        update(IngestJob)
        .where(IngestJob.id == job_id)
        .values(status="running", thread_id=thread_id, heartbeat_at=now, updated_at=now)
    )


async def touch_job_heartbeat(session: AsyncSession, job_id: int) -> None:
    now = _utcnow()
    await session.execute(
        update(IngestJob)
        .where(IngestJob.id == job_id)
        .values(heartbeat_at=now, updated_at=now)
    )


async def complete_job(session: AsyncSession, job_id: int, *, failed: bool = False, error: str | None = None) -> None:
    now = _utcnow()
    await session.execute(
        update(IngestJob)
        .where(IngestJob.id == job_id)
        .values(
            status="failed" if failed else "completed",
            error_message=error,
            heartbeat_at=now,
            updated_at=now,
        )
    )


async def reconcile_stale_jobs(session: AsyncSession, settings: Settings | None = None) -> int:
    settings = settings or get_settings()
    cutoff = _utcnow() - timedelta(minutes=settings.job_stale_minutes)
    result = await session.execute(
        update(IngestJob)
        .where(
            IngestJob.status.in_(("claimed", "running")),
            IngestJob.heartbeat_at.is_not(None),
            IngestJob.heartbeat_at < cutoff,
        )
        .values(status="pending", claimed_by=None, thread_id=None, updated_at=_utcnow())
    )
    return result.rowcount or 0
