from app.core.config import Settings, get_settings
from app.runtime.dbos_app import get_dbos, launch_dbos, destroy_dbos

# Import at module level so DBOS workflow/step decorators are registered
# before any launch_dbos() call inside the tests below.
from app.runtime.dbos_ingest import ingest_source_workflow  # noqa: F401
from app.runtime.ingest_runner import IngestRunner


def test_get_dbos_is_idempotent_and_launches():
    settings = get_settings()
    d1 = get_dbos(settings)
    d2 = get_dbos(settings)
    assert d1 is d2  # singleton
    launch_dbos(settings)  # must not raise against test Postgres
    destroy_dbos()


def test_workflow_runs_and_returns_status(create_source):
    # Test env has no reachable LLM, so the wrapped pipeline fails — but the workflow
    # still routes + executes the real pipeline and returns a structured result.
    source = create_source(status="pending", content_text="hello world")
    launch_dbos()
    try:
        result = ingest_source_workflow(source.id, None)
    finally:
        destroy_dbos()
    assert result["source_id"] == source.id
    assert "status" in result


def test_runner_routes_to_dbos(create_source):
    import asyncio as _asyncio
    source = create_source(status="pending", content_text="routing test")
    settings = Settings(INGEST_ORCHESTRATOR="dbos")
    launch_dbos(settings)
    try:
        result = _asyncio.run(IngestRunner(settings).run(source.id, job_id=None))
    finally:
        destroy_dbos()
    assert result["source_id"] == source.id
    assert "status" in result


def test_dbos_step_does_not_poison_global_engine_under_concurrent_use(create_source):
    """Regression: the DBOS step must run on its own loop-local engine, so the
    worker loop's GLOBAL engine stays usable concurrently (heartbeat / job status)
    and afterward. The old global-engine-dispose approach broke exactly this."""
    import asyncio

    from sqlalchemy import text

    from app.core.database import async_session_maker
    from app.models.ingest_job import IngestJob
    from app.services.ingest_job_service import (
        complete_job,
        enqueue_ingest_job,
        touch_job_heartbeat,
    )
    from tests.conftest import run_async

    source = create_source(status="pending", content_text="concurrency probe")
    settings = Settings(INGEST_ORCHESTRATOR="dbos")
    launch_dbos(settings)

    async def _scenario():
        async with async_session_maker() as session:
            job = await enqueue_ingest_job(session, source.id)
            await session.commit()
            jid = job.id

        beats_ok = 0

        async def _beats():
            # Hammer the GLOBAL engine on this (worker) loop while the DBOS step
            # runs the pipeline on its own loop/engine in an executor thread.
            nonlocal beats_ok
            for _ in range(5):
                async with async_session_maker() as s:
                    await touch_job_heartbeat(s, jid)
                    await s.commit()
                beats_ok += 1
                await asyncio.sleep(0.05)

        run_task = asyncio.create_task(
            IngestRunner(settings).run(source.id, job_id=jid)
        )
        beat_task = asyncio.create_task(_beats())
        result = await run_task
        await beat_task

        async with async_session_maker() as session:
            await complete_job(
                session,
                jid,
                failed=(result.get("status") == "failed"),
                error=result.get("error"),
            )
            await session.commit()
        # Global engine must still be healthy after the step finished.
        async with async_session_maker() as session:
            ping = (await session.execute(text("SELECT 1"))).scalar()
            final = await session.get(IngestJob, jid)
        return result, beats_ok, ping, final.status

    try:
        result, beats_ok, ping, status = run_async(_scenario())
    finally:
        destroy_dbos()

    assert result["source_id"] == source.id
    assert beats_ok == 5, "global-engine heartbeats must succeed concurrently with the DBOS step"
    assert ping == 1, "global engine must remain usable after the DBOS step"
    assert status in {"completed", "failed"}
