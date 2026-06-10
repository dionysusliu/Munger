"""DB-backed ingest job queue lifecycle characterization."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import update

from app.core.config import get_settings
from app.core.database import async_session_maker
from app.models.ingest_job import IngestJob
from app.services.ingest_job_service import (
    claim_pending_jobs,
    complete_job,
    enqueue_ingest_job,
    mark_job_running,
    reconcile_stale_jobs,
    touch_job_heartbeat,
)
from tests.conftest import run_async


def test_enqueue_is_idempotent_per_source(create_source):
    source = create_source(status="pending")

    async def _inner():
        async with async_session_maker() as session:
            j1 = await enqueue_ingest_job(session, source.id)
            await session.commit()
            j1_id = j1.id
        async with async_session_maker() as session:
            j2 = await enqueue_ingest_job(session, source.id)
            await session.commit()
            j2_id = j2.id
        return j1_id, j2_id

    a, b = run_async(_inner())
    assert a == b, "a second enqueue for an active source must return the same job"


def test_claim_then_run_then_complete(create_source):
    source = create_source(status="pending")

    async def _inner():
        async with async_session_maker() as session:
            job = await enqueue_ingest_job(session, source.id)
            await session.commit()
            jid = job.id
        async with async_session_maker() as session:
            claimed = await claim_pending_jobs(session, worker_id="w1", limit=5)
            await session.commit()
            claimed_ids = [c.id for c in claimed]
        async with async_session_maker() as session:
            await mark_job_running(session, jid, "thread-1")
            await touch_job_heartbeat(session, jid)
            await complete_job(session, jid, failed=False, error=None)
            await session.commit()
        async with async_session_maker() as session:
            final = await session.get(IngestJob, jid)
            return claimed_ids, final.status

    claimed_ids, status = run_async(_inner())
    assert claimed_ids and claimed_ids[0] is not None
    assert status == "completed"


def test_reconcile_requeues_stale_running_job(create_source):
    source = create_source(status="pending")
    settings = get_settings()

    async def _inner():
        async with async_session_maker() as session:
            job = await enqueue_ingest_job(session, source.id)
            await session.commit()
            jid = job.id
        async with async_session_maker() as session:
            await mark_job_running(session, jid, "thread-stale")
            stale_ts = datetime.now(timezone.utc) - timedelta(minutes=settings.job_stale_minutes + 5)
            await session.execute(
                update(IngestJob).where(IngestJob.id == jid).values(heartbeat_at=stale_ts)
            )
            await session.commit()
        async with async_session_maker() as session:
            n = await reconcile_stale_jobs(session, settings)
            await session.commit()
        async with async_session_maker() as session:
            final = await session.get(IngestJob, jid)
            return n, final.status

    requeued, status = run_async(_inner())
    assert requeued >= 1
    assert status == "pending", "stale running job must be requeued to pending"
