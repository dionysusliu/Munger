"""Node factory for the ``intake`` subgraph: register, parse, hash_dedup, skip."""

from __future__ import annotations

import logging

from sqlalchemy import select, update

from app.core.database import async_session_maker
from app.models.ingest_job import IngestJob
from app.models.source import Source
from app.runtime.context import RuntimeServices
from app.runtime.db_helpers import fail_source, log_ingestion, update_source_status
from app.runtime.events import record_ingest_event
from app.runtime.pipeline_events import pipeline_step
from app.services.ingest_job_service import complete_job

logger = logging.getLogger(__name__)


def make_intake_nodes(services: RuntimeServices) -> dict:
    """Return a dict of async node functions keyed by node name."""

    async def n_register(state: dict) -> dict:
        """Mark source as ``extracting``; validates source exists."""
        source_id: int = state["source_id"]
        job_id: int | None = state.get("job_id")

        async with pipeline_step(source_id=source_id, job_id=job_id, step_key="register_source", llm=services.llm):
            async with async_session_maker() as session:
                source = await session.get(Source, source_id)
                if source is None:
                    msg = f"Source {source_id} not found"
                    await fail_source(source_id, msg)
                    raise ValueError(msg)
                source.status = "extracting"
                await session.commit()

        return {}

    async def n_parse(state: dict) -> dict:
        """Extract raw text from the source file; caches result in sources.content_text."""
        source_id: int = state["source_id"]
        job_id: int | None = state.get("job_id")

        async with pipeline_step(
            source_id=source_id, job_id=job_id, step_key="parse_document", llm=services.llm
        ) as metrics:
            async with async_session_maker() as session:
                source = await session.get(Source, source_id)
                if source is None:
                    msg = f"Source {source_id} not found"
                    await fail_source(source_id, msg)
                    raise ValueError(msg)

                if source.content_text:
                    metrics["chars"] = len(source.content_text)
                    return {"content_text": source.content_text}

                if not services.storage:
                    msg = "Storage service not available"
                    await fail_source(source_id, msg)
                    raise ValueError(msg)

                text = await services.storage.extract_text(source.file_path, source.file_type)
                if not text:
                    msg = "No text could be extracted"
                    await fail_source(source_id, msg)
                    raise ValueError(msg)

                source.content_text = text
                await session.commit()
                metrics["chars"] = len(text)

        return {"content_text": text}

    async def n_hash_dedup(state: dict) -> dict:
        """Check whether another Source already has the same content_hash.

        This guards worker-triggered re-ingest; normal upload dedup happens at
        the API layer (HTTP 409).  Sets ``is_duplicate`` / ``duplicate_of_source_id``.
        """
        source_id: int = state["source_id"]
        job_id: int | None = state.get("job_id")

        async with pipeline_step(
            source_id=source_id, job_id=job_id, step_key="hash_dedup", llm=services.llm
        ) as metrics:
            async with async_session_maker() as session:
                source = await session.get(Source, source_id)
                if source is None:
                    return {"is_duplicate": False, "duplicate_of_source_id": None}

                result = await session.execute(
                    select(Source)
                    .where(
                        Source.content_hash == source.content_hash,
                        Source.id != source_id,
                        Source.status == "completed",
                    )
                    .limit(1)
                )
                existing = result.scalar_one_or_none()

            if existing:
                metrics["duplicate_of"] = existing.id
                return {"is_duplicate": True, "duplicate_of_source_id": existing.id}

        return {"is_duplicate": False, "duplicate_of_source_id": None}

    async def n_skip(state: dict) -> dict:
        """Mark source as ``skipped_duplicate`` and complete the job without running cognify."""
        source_id: int = state["source_id"]
        job_id: int | None = state.get("job_id")
        duplicate_of: int | None = state.get("duplicate_of_source_id")

        await update_source_status(source_id, "skipped_duplicate")
        await log_ingestion(source_id, f"Skipped: duplicate of source {duplicate_of}")

        if job_id is not None:
            async with async_session_maker() as session:
                await complete_job(session, job_id)
                await session.commit()

        await record_ingest_event(
            source_id=source_id,
            job_id=job_id,
            event_type="status_change",
            payload={
                "status": "skipped_duplicate",
                "duplicate_of_source_id": duplicate_of,
            },
        )
        return {"status": "skipped_duplicate"}

    return {
        "n_register": n_register,
        "n_parse": n_parse,
        "n_hash_dedup": n_hash_dedup,
        "n_skip": n_skip,
    }


def is_duplicate(state: dict) -> str:
    """Conditional edge predicate for ``n_hash_dedup`` → skip or cognify."""
    return "n_skip" if state.get("is_duplicate") else "__end__"


make_add_nodes = make_intake_nodes
