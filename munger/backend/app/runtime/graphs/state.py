"""Typed state schemas for the ingest LangGraph subgraphs."""

from __future__ import annotations

from typing import Annotated, TypedDict


def merge_dicts(left: dict, right: dict) -> dict:
    """LangGraph reducer: merge right into left (last-write-wins per key)."""
    merged = left.copy()
    merged.update(right)
    return merged


class IntakeState(TypedDict, total=False):
    """State for the ``intake`` subgraph (register → parse → hash-dedup → skip?)."""

    source_id: int
    job_id: int | None
    file_path: str
    file_type: str
    content_text: str
    is_duplicate: bool
    duplicate_of_source_id: int | None


AddState = IntakeState  # backward-compatible alias


class ChunkMapState(TypedDict, total=False):
    """Isolated per-chunk subgraph state used by the LangGraph Send pattern."""

    source_id: int
    job_id: int | None
    chunk_id: int
    map_result: dict  # entities_raw, relationships_raw, glean_entities_added


class CognifyState(TypedDict, total=False):
    """State for the ``cognify`` subgraph (chunk → map → reduce → link → wiki → finalize)."""

    source_id: int
    job_id: int | None
    chunk_ids: list[int]
    map_retry_wave: int
    # Annotated reducer: merge per-chunk Send results into a single dict
    map_metrics: Annotated[dict, merge_dicts]
    reduce_metrics: dict
    link_metrics: dict
    summary_chars: int
    wiki_metrics: dict
    error: str | None
    status: str


class IngestState(IntakeState, CognifyState, total=False):
    """Parent graph state = union of IntakeState + CognifyState."""
