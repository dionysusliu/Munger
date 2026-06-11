"""Operator-facing pipeline step events (OTel-ready payloads)."""

from __future__ import annotations

import time
from contextlib import asynccontextmanager
from typing import Any

from app.runtime.events import record_ingest_event

STEP_LABELS: dict[str, str] = {
    # Graph subgraph steps (GRAPH_STEP_ORDER)
    "register_source": "Registering source",
    "parse_document": "Reading document",
    "hash_dedup": "Checking for duplicates",
    "chunk_document": "Splitting into sections",
    "map_chunks": "Mapping chunks",
    "reduce_entities": "Merging entities",
    "link_entities": "Linking entities",
    "summarize_source": "Writing summary",
    "generate_wiki_pages": "Creating wiki pages",
    "link_wiki_pages": "Linking pages",
    "finalize_ingest": "Finishing up",
    # Deprecated (normalization-only)
    "extract_entities_from_chunks": "Extracting entities",
    "glean_entities": "Refining extraction",
    "resolve_entities": "Matching entities",
}

# Canonical order for graph subgraph orchestration (11 steps).
# Used as the primary step registry; replaces INGEST_TOOL_ORDER for new runs.
GRAPH_STEP_ORDER: list[str] = [
    "register_source",
    "parse_document",
    "hash_dedup",
    "chunk_document",
    "map_chunks",
    "reduce_entities",
    "link_entities",
    "summarize_source",
    "generate_wiki_pages",
    "link_wiki_pages",
    "finalize_ingest",
]

# Legacy 8-step order kept for agent-path backward compatibility.
INGEST_TOOL_ORDER: list[str] = [
    "parse_document",
    "chunk_document",
    "map_chunks",
    "reduce_entities",
    "summarize_source",
    "generate_wiki_pages",
    "link_wiki_pages",
    "finalize_ingest",
]

# Multi-step composite aliases: normalization-only, not exposed in progressive gating.
COMPOSITE_ALIASES: frozenset[str] = frozenset({"extract_entities_from_text"})

TOOL_ALIASES: dict[str, str] = {
    "extract_source_text": "parse_document",
    "extract_entities_from_text": "map_chunks",
    "create_wiki_pages": "generate_wiki_pages",
    # Deprecated one-release aliases
    "extract_entities_from_chunks": "map_chunks",
    "glean_entities": "map_chunks",
    "resolve_entities": "reduce_entities",
}

CANONICAL_TOOL_ORDER = GRAPH_STEP_ORDER


def canonical_tool_name(name: str) -> str:
    return TOOL_ALIASES.get(name, name)


def step_index(step_key: str) -> int:
    key = canonical_tool_name(step_key)
    try:
        return GRAPH_STEP_ORDER.index(key) + 1
    except ValueError:
        return 0


async def emit_pipeline_step_start(
    *,
    source_id: int,
    job_id: int | None,
    step_key: str,
) -> None:
    key = canonical_tool_name(step_key)
    await record_ingest_event(
        source_id=source_id,
        job_id=job_id,
        event_type="pipeline_step_start",
        payload={
            "step_key": key,
            "step_index": step_index(key),
            "step_total": len(GRAPH_STEP_ORDER),
            "label": STEP_LABELS.get(key, key),
            "tool_name": key,
        },
    )


async def emit_pipeline_step_complete(
    *,
    source_id: int,
    job_id: int | None,
    step_key: str,
    duration_ms: int,
    metrics: dict[str, Any] | None = None,
) -> None:
    key = canonical_tool_name(step_key)
    await record_ingest_event(
        source_id=source_id,
        job_id=job_id,
        event_type="pipeline_step_complete",
        payload={
            "step_key": key,
            "step_index": step_index(key),
            "step_total": len(GRAPH_STEP_ORDER),
            "label": STEP_LABELS.get(key, key),
            "duration_ms": duration_ms,
            "metrics": metrics or {},
        },
    )


async def emit_pipeline_step_failed(
    *,
    source_id: int,
    job_id: int | None,
    step_key: str,
    message: str,
) -> None:
    key = canonical_tool_name(step_key)
    await record_ingest_event(
        source_id=source_id,
        job_id=job_id,
        event_type="pipeline_step_failed",
        payload={"step_key": key, "message": message},
    )


async def emit_pipeline_summary(
    *,
    source_id: int,
    job_id: int | None,
    metrics: dict[str, Any],
) -> None:
    await record_ingest_event(
        source_id=source_id,
        job_id=job_id,
        event_type="pipeline_summary",
        payload=metrics,
    )


@asynccontextmanager
async def pipeline_step(
    *,
    source_id: int,
    job_id: int | None,
    step_key: str,
    llm=None,
):
    """Async context manager that emits pipeline step start/complete/failed events.

    Optional ``llm`` kwarg: any object with a ``stats`` dict (e.g. LLMService).
    When provided, the manager snapshots stats before ``yield`` and injects the
    delta into ``metrics`` as ``llm_calls`` / ``llm_ms`` after the step body.
    Objects without ``.stats`` (e.g. ScriptedLLMService) are silently skipped.
    """
    await emit_pipeline_step_start(source_id=source_id, job_id=job_id, step_key=step_key)
    start = time.perf_counter()
    metrics: dict[str, Any] = {}

    # Snapshot LLM counters before entering the step body.
    llm_stats = getattr(llm, "stats", None)
    before_calls: int = llm_stats["calls"] if llm_stats is not None else 0
    before_ms: int = llm_stats["ms"] if llm_stats is not None else 0

    try:
        yield metrics
        duration_ms = int((time.perf_counter() - start) * 1000)

        # Inject LLM telemetry delta when at least one call occurred this step.
        if llm_stats is not None:
            delta_calls = llm_stats["calls"] - before_calls
            delta_ms = llm_stats["ms"] - before_ms
            if delta_calls > 0:
                metrics.setdefault("llm_calls", delta_calls)
                metrics.setdefault("llm_ms", delta_ms)

        await emit_pipeline_step_complete(
            source_id=source_id,
            job_id=job_id,
            step_key=step_key,
            duration_ms=duration_ms,
            metrics=metrics,
        )
    except Exception as exc:
        await emit_pipeline_step_failed(
            source_id=source_id,
            job_id=job_id,
            step_key=step_key,
            message=str(exc),
        )
        raise
