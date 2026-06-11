"""Entry point for running the ingest pipeline.

Branches on ``settings.ingest_orchestrator``:
- ``"graph"`` (default): compiled LangGraph parent graph (add + cognify subgraphs).
- ``"agent"``: legacy LangChain agent (rollback escape hatch).
"""

from __future__ import annotations

import logging
from uuid import uuid4

from langchain_core.messages import AIMessage, HumanMessage

from app.core.config import Settings, get_settings
from app.runtime.agents.ingest_lead_agent import make_ingest_lead_agent
from app.runtime.context import RuntimeServices
from app.runtime.db_helpers import fail_source, get_source
from app.runtime.events import record_ingest_event, serialize_langchain_message
from app.runtime.harness.checkpointer import get_async_checkpointer
from app.runtime.state import IngestRunState
from app.observability.langsmith_setup import ingest_run_config, ingest_tracing_session, merge_tracing_config
from app.services.llm_service import LLMError, LLMService

logger = logging.getLogger(__name__)


class IngestRunner:
    """Runs the ingest lead agent for a single source."""

    def __init__(self, settings: Settings | None = None, services: RuntimeServices | None = None):
        self.settings = settings or get_settings()
        self._services = services

    def _build_services(self) -> RuntimeServices:
        if self._services is not None:
            return self._services

        llm_service = None
        try:
            llm_service = LLMService(self.settings)
        except LLMError as exc:
            logger.warning("LLM service unavailable: %s", exc)

        return RuntimeServices.from_settings(self.settings, llm=llm_service)

    async def _persist_message_events(
        self,
        *,
        source_id: int,
        job_id: int | None,
        message: object,
    ) -> None:
        msg_type = getattr(message, "type", "")
        if msg_type == "ai":
            payload = serialize_langchain_message(message)
            await record_ingest_event(
                source_id=source_id,
                job_id=job_id,
                event_type="agent_message",
                payload=payload,
            )
            for tc in getattr(message, "tool_calls", None) or []:
                await record_ingest_event(
                    source_id=source_id,
                    job_id=job_id,
                    event_type="tool_call",
                    payload={
                        "id": tc.get("id"),
                        "name": tc.get("name"),
                        "args": tc.get("args", {}),
                    },
                )
        elif msg_type == "tool":
            await record_ingest_event(
                source_id=source_id,
                job_id=job_id,
                event_type="tool_result",
                payload=serialize_langchain_message(message),
            )

    async def run(
        self,
        source_id: int,
        job_id: int | None = None,
        orchestrator: str | None = None,
        use_checkpointer: bool = True,
    ) -> IngestRunState:
        orchestrator = orchestrator or self.settings.ingest_orchestrator
        logger.info(
            "Starting ingest for source %s (job=%s, orchestrator=%s)",
            source_id,
            job_id,
            orchestrator,
        )

        if orchestrator == "dbos":
            # Durable spine: start the DBOS workflow, which runs the pipeline
            # (forced to "graph") inside its own event loop. Do NOT build services
            # or the checkpointer on this (outer) loop — the workflow owns them,
            # bound to the step's loop.
            from app.runtime.dbos_ingest import run_via_dbos

            return await run_via_dbos(source_id, job_id)

        services = self._build_services()

        if not services.llm:
            message = "LLM service not available"
            await fail_source(source_id, message)
            await record_ingest_event(
                source_id=source_id,
                job_id=job_id,
                event_type="error",
                payload={"message": message},
            )
            return {"source_id": source_id, "error": message, "status": "failed"}

        # The DBOS path runs the graph with no LangGraph checkpointer (DBOS itself
        # provides durability), avoiding a loop-bound Postgres checkpointer pool
        # inside the step thread.
        checkpointer = await get_async_checkpointer(self.settings) if use_checkpointer else None

        if orchestrator == "graph":
            return await self._run_graph(
                source_id=source_id,
                job_id=job_id,
                services=services,
                checkpointer=checkpointer,
            )

        return await self._run_agent(
            source_id=source_id,
            job_id=job_id,
            services=services,
            checkpointer=checkpointer,
        )

    # ------------------------------------------------------------------
    # Graph path (LangGraph StateGraph subgraphs)
    # ------------------------------------------------------------------

    async def _run_graph(
        self,
        *,
        source_id: int,
        job_id: int | None,
        services: RuntimeServices,
        checkpointer,
    ) -> IngestRunState:
        from app.runtime.graphs.ingest import build_ingest_graph

        graph = build_ingest_graph(services, checkpointer)

        run_nonce = uuid4().hex[:8]
        thread_id = f"ingest-{source_id}-{run_nonce}"
        config = ingest_run_config(
            thread_id=thread_id,
            source_id=source_id,
            job_id=job_id,
            recursion_limit=self.settings.max_agent_steps * 4,
        )

        await record_ingest_event(
            source_id=source_id,
            job_id=job_id,
            event_type="status_change",
            payload={"status": "running", "thread_id": thread_id},
        )

        try:
            with ingest_tracing_session(self.settings) as trace_cfg:
                run_config = merge_tracing_config(config, trace_cfg)
                await graph.ainvoke(
                    {"source_id": source_id, "job_id": job_id},
                    config=run_config,
                )
        except Exception as exc:
            message = f"Ingest graph failed: {exc or exc.__class__.__name__}"
            logger.exception("Ingest graph failed for source %s", source_id)
            await fail_source(source_id, message)
            await record_ingest_event(
                source_id=source_id,
                job_id=job_id,
                event_type="error",
                payload={"message": message},
            )
            return {
                "source_id": source_id,
                "error": message,
                "status": "failed",
                "thread_id": thread_id,
            }

        source = await get_source(source_id)
        status = source.status if source else "unknown"
        await record_ingest_event(
            source_id=source_id,
            job_id=job_id,
            event_type="status_change",
            payload={"status": status},
        )
        return {"source_id": source_id, "status": status, "thread_id": thread_id}

    # ------------------------------------------------------------------
    # Agent path (legacy LangChain agent + gating middleware)
    # ------------------------------------------------------------------

    async def _run_agent(
        self,
        *,
        source_id: int,
        job_id: int | None,
        services: RuntimeServices,
        checkpointer,
    ) -> IngestRunState:
        skill_name = "ingest"
        if job_id is not None:
            from app.core.database import async_session_maker
            from app.models.ingest_job import IngestJob

            async with async_session_maker() as session:
                job = await session.get(IngestJob, job_id)
                if job and job.skill_name:
                    skill_name = job.skill_name

        agent = make_ingest_lead_agent(
            services, checkpointer, job_id=job_id, skill_name=skill_name
        )

        run_nonce = uuid4().hex[:8]
        thread_id = f"ingest-{source_id}-{run_nonce}"
        config = ingest_run_config(
            thread_id=thread_id,
            source_id=source_id,
            job_id=job_id,
            skill_name=skill_name,
            recursion_limit=self.settings.max_agent_steps,
        )

        await record_ingest_event(
            source_id=source_id,
            job_id=job_id,
            event_type="status_change",
            payload={"status": "running", "thread_id": thread_id},
        )

        try:
            with ingest_tracing_session(self.settings) as trace_cfg:
                run_config = merge_tracing_config(config, trace_cfg)
                async for event in agent.astream_events(
                    {
                        "messages": [
                            HumanMessage(
                                content=f"Ingest source {source_id}. Use source_id={source_id} for all tools."
                            )
                        ]
                    },
                    config=run_config,
                    version="v2",
                ):
                    event_name = event.get("event")
                    data = event.get("data", {})
                    if event_name == "on_chat_model_end":
                        output = data.get("output")
                        message = getattr(output, "message", output)
                        if isinstance(message, AIMessage):
                            await self._persist_message_events(
                                source_id=source_id, job_id=job_id, message=message
                            )
                    elif event_name == "on_tool_end":
                        tool_output = data.get("output")
                        if tool_output is not None:
                            await record_ingest_event(
                                source_id=source_id,
                                job_id=job_id,
                                event_type="tool_result",
                                payload={
                                    "name": data.get("name") or getattr(tool_output, "name", None),
                                    "content": getattr(tool_output, "content", str(tool_output)),
                                },
                            )

        except Exception as exc:
            message = f"Ingest agent failed: {exc or exc.__class__.__name__}"
            logger.exception("Ingest agent failed for source %s", source_id)
            await fail_source(source_id, message)
            await record_ingest_event(
                source_id=source_id,
                job_id=job_id,
                event_type="error",
                payload={"message": message},
            )
            return {
                "source_id": source_id,
                "error": message,
                "status": "failed",
                "thread_id": thread_id,
            }

        source = await get_source(source_id)
        status = source.status if source else "unknown"
        await record_ingest_event(
            source_id=source_id,
            job_id=job_id,
            event_type="status_change",
            payload={"status": status},
        )
        return {"source_id": source_id, "status": status, "thread_id": thread_id}
