"""Ingest worker loop."""

from __future__ import annotations

import asyncio
import logging

from app.core.config import get_settings
from app.core.database import async_session_maker
from app.runtime.ingest_runner import IngestRunner
from app.services.ingest_job_service import claim_pending_jobs, complete_job, mark_job_running, reconcile_stale_jobs, touch_job_heartbeat

logger = logging.getLogger(__name__)


async def _heartbeat_loop(job_id: int, interval_sec: int, stop_event: asyncio.Event) -> None:
    while not stop_event.is_set():
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval_sec)
            break
        except asyncio.TimeoutError:
            async with async_session_maker() as session:
                await touch_job_heartbeat(session, job_id)
                await session.commit()


async def _execute_job(job_id: int, source_id: int) -> None:
    settings = get_settings()
    stop_event = asyncio.Event()
    heartbeat_task = asyncio.create_task(
        _heartbeat_loop(job_id, settings.job_heartbeat_interval_sec, stop_event)
    )
    failed = False
    error: str | None = None
    async with async_session_maker() as session:
        await mark_job_running(session, job_id, f"pending-{job_id}")
        await session.commit()
    try:
        runner = IngestRunner(settings)
        result = await runner.run(source_id, job_id=job_id)
        thread_id = result.get("thread_id")
        if thread_id:
            async with async_session_maker() as session:
                await mark_job_running(session, job_id, thread_id)
                await session.commit()
        failed = result.get("status") == "failed" or bool(result.get("error"))
        error = result.get("error")
    except Exception as exc:
        failed = True
        error = str(exc)
        logger.exception("Worker failed job %s for source %s", job_id, source_id)
    finally:
        stop_event.set()
        await heartbeat_task
        async with async_session_maker() as session:
            await complete_job(session, job_id, failed=failed, error=error)
            await session.commit()


async def run_worker_forever() -> None:
    settings = get_settings()

    logger.info(
        "Starting ingest worker id=%s concurrency=%s",
        settings.worker_id,
        settings.worker_concurrency,
    )

    async with async_session_maker() as session:
        requeued = await reconcile_stale_jobs(session, settings)
        await session.commit()
        if requeued:
            logger.warning("Requeued %s stale ingest jobs", requeued)

    semaphore = asyncio.Semaphore(settings.worker_concurrency)
    in_flight: set[asyncio.Task] = set()

    while True:
        slots = settings.worker_concurrency - len(in_flight)
        if slots > 0:
            async with async_session_maker() as session:
                jobs = await claim_pending_jobs(session, worker_id=settings.worker_id, limit=slots)
                await session.commit()

            for job in jobs:
                await semaphore.acquire()

                async def _run(job_id: int, source_id: int) -> None:
                    try:
                        await _execute_job(job_id, source_id)
                    finally:
                        semaphore.release()

                task = asyncio.create_task(_run(job.id, job.source_id))
                in_flight.add(task)
                task.add_done_callback(in_flight.discard)

        if not in_flight:
            await asyncio.sleep(1.0)
        else:
            await asyncio.sleep(0.5)
