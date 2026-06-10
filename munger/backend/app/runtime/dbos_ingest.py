"""Durable DBOS workflow wrapping the existing ingest pipeline (SP1.1).

Strangler step: the workflow runs the current async pipeline (forced to the
``graph`` orchestrator to avoid recursing back into DBOS) inside a single
durable step. Later sub-projects decompose this into per-stage steps.
"""

from __future__ import annotations

import asyncio
import logging

from dbos import DBOS

from app.core.config import get_settings
from app.runtime.ingest_runner import IngestRunner
from app.runtime.state import IngestRunState

logger = logging.getLogger(__name__)


async def _run_pipeline_async(source_id: int, job_id: int | None) -> IngestRunState:
    # Dispose pooled connections from the previous event loop.
    # asyncio.run() creates a fresh event loop per DBOS step thread;
    # psycopg3 async connections are bound to the loop they were created in,
    # so pooled connections from a prior loop would hang when reused.
    from app.core.database import engine
    await engine.dispose()
    # Reset the checkpointer singleton so it is recreated in this event loop.
    # psycopg_pool.AsyncConnectionPool is also loop-bound.
    from app.runtime.harness.checkpointer import reset_checkpointer
    await reset_checkpointer()
    # Force "graph" so we reuse the existing pipeline and never recurse into dbos.
    runner = IngestRunner(get_settings())
    return await runner.run(source_id, job_id=job_id, orchestrator="graph")


@DBOS.step()
def ingest_pipeline_step(source_id: int, job_id: int | None) -> IngestRunState:
    # DBOS runs steps in their own threads (no running event loop), so asyncio.run is safe.
    return asyncio.run(_run_pipeline_async(source_id, job_id))


@DBOS.workflow()
def ingest_source_workflow(source_id: int, job_id: int | None) -> IngestRunState:
    return ingest_pipeline_step(source_id, job_id)


async def run_via_dbos(source_id: int, job_id: int | None) -> IngestRunState:
    """Start the durable workflow from async code, bridging to DBOS's sync API."""
    loop = asyncio.get_running_loop()

    def _start_and_wait() -> IngestRunState:
        handle = DBOS.start_workflow(ingest_source_workflow, source_id, job_id)
        return handle.get_result()

    return await loop.run_in_executor(None, _start_and_wait)
