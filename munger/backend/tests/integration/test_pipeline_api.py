"""
Pipeline topology + source job-history endpoint tests.

Tests call handlers directly (no TestClient) — consistent with project conventions.
Route registration is verified via app.routes inspection.
"""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import insert

from app.core.database import async_session_maker
from app.models.ingest_event import IngestEvent
from app.models.ingest_job import IngestJob
from tests.conftest import run_async


# ---------------------------------------------------------------------------
# test_topology_shape
# ---------------------------------------------------------------------------


def test_topology_shape():
    """topology_endpoint() returns 11 stages with correct shape, groups, and flags."""
    from app.api.pipeline import topology_endpoint

    result = run_async(topology_endpoint())

    assert result["total"] == 11
    stages = result["stages"]
    assert len(stages) == 11

    # First stage
    first = stages[0]
    assert first["key"] == "register_source"
    assert first["group"] == "intake"
    assert first["index"] == 0

    # Intake group stages
    intake_keys = {s["key"] for s in stages if s["group"] == "intake"}
    assert intake_keys == {"register_source", "parse_document", "hash_dedup"}

    # map_chunks: fan_out, cognify group
    map_chunks_stage = next(s for s in stages if s["key"] == "map_chunks")
    assert map_chunks_stage["fan_out"] is True
    assert map_chunks_stage["group"] == "cognify"

    # All other stages: fan_out is False
    for s in stages:
        if s["key"] != "map_chunks":
            assert s["fan_out"] is False

    # All labels non-empty strings
    for s in stages:
        assert isinstance(s["label"], str) and s["label"]

    # Index values are 0-based sequential
    assert [s["index"] for s in stages] == list(range(11))


# ---------------------------------------------------------------------------
# test_source_jobs_with_event_durations
# ---------------------------------------------------------------------------


def test_source_jobs_with_event_durations(create_source):
    """list_source_jobs returns newest-first with duration_ms for evented job, None for other."""
    from app.api.sources import list_source_jobs

    source = create_source(title="JobHistorySource")

    t0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    t1 = t0 + timedelta(seconds=5)   # 5000 ms span

    async def _seed():
        async with async_session_maker() as session:
            # Older job (id lower) — no events
            job_old = IngestJob(source_id=source.id, status="completed")
            session.add(job_old)
            await session.flush()
            old_id = job_old.id

            # Newer job (id higher) — two events spanning 5 s
            job_new = IngestJob(source_id=source.id, status="completed")
            session.add(job_new)
            await session.flush()
            new_id = job_new.id

            # Insert events with explicit created_at for the newer job
            await session.execute(
                insert(IngestEvent).values(
                    source_id=source.id,
                    job_id=new_id,
                    event_type="pipeline_step_start",
                    payload={},
                    created_at=t0,
                )
            )
            await session.execute(
                insert(IngestEvent).values(
                    source_id=source.id,
                    job_id=new_id,
                    event_type="pipeline_step_complete",
                    payload={},
                    created_at=t1,
                )
            )
            await session.commit()
            return old_id, new_id

    old_id, new_id = run_async(_seed())

    async def _call():
        # list_source_jobs needs a db session; call via handler using a fresh session
        async with async_session_maker() as db:
            return await list_source_jobs(source_id=source.id, db=db)

    result = run_async(_call())

    assert result["source_id"] == source.id
    jobs = result["jobs"]
    assert len(jobs) == 2

    # newest-first: new_id should come before old_id
    assert jobs[0]["id"] == new_id
    assert jobs[1]["id"] == old_id

    # newer job: duration_ms should be ≈ 5000 ms
    assert jobs[0]["duration_ms"] == 5000

    # older job: no events → None
    assert jobs[1]["duration_ms"] is None

    # status and timestamps present
    assert jobs[0]["status"] == "completed"
    assert jobs[0]["created_at"] is not None


# ---------------------------------------------------------------------------
# test_pipeline_routes_registered
# ---------------------------------------------------------------------------


def test_pipeline_routes_registered():
    """/api/pipeline/topology and /api/sources/{source_id}/jobs are registered in the app."""
    from app.main import app

    paths = {getattr(r, "path", None) for r in app.routes}
    assert "/api/pipeline/topology" in paths
    assert "/api/sources/{source_id}/jobs" in paths
