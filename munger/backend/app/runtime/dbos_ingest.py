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
    # This coroutine runs in the DBOS step's own thread + fresh event loop
    # (asyncio.run). psycopg3 async connections are loop-bound, so we must NOT
    # reuse the worker loop's global engine here. Bind a step-local engine via the
    # database module's ContextVar — isolated to this context — so the worker
    # loop's concurrent heartbeat / job-status writes keep using the global engine
    # without cross-loop corruption. Two concurrent steps each get their own
    # engine + ContextVar binding (no shared mutable global pool).
    import app.core.database as db
    from sqlalchemy.ext.asyncio import (
        AsyncSession,
        async_sessionmaker,
        create_async_engine,
    )

    step_engine = create_async_engine(db.DATABASE_URL, future=True)
    step_session_maker = async_sessionmaker(
        step_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    token = db._session_maker_var.set(step_session_maker)
    try:
        # Force "graph" (never recurse into dbos) and skip the LangGraph
        # checkpointer — DBOS provides durability, and a Postgres checkpointer pool
        # would be loop-bound to this short-lived step loop.
        runner = IngestRunner(get_settings())
        return await runner.run(
            source_id, job_id=job_id, orchestrator="graph", use_checkpointer=False
        )
    finally:
        db._session_maker_var.reset(token)
        await step_engine.dispose()


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
