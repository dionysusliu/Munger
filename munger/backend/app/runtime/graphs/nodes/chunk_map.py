"""Per-chunk subgraph and process_chunk node for the LangGraph Send map-reduce pattern."""

from __future__ import annotations

import logging

from langgraph.graph import END, START, StateGraph

from app.runtime.context import RuntimeServices
from app.runtime.graphs.state import ChunkMapState

logger = logging.getLogger(__name__)


def build_chunk_map_subgraph(services: RuntimeServices):
    """Compile a standalone StateGraph(ChunkMapState) for isolated per-chunk processing.

    Useful for unit tests and as the body of process_chunk in the Send pattern.
    """
    if not services.map_chunks:
        raise ValueError("MapChunkService required for chunk_map_subgraph")

    graph = StateGraph(ChunkMapState)

    async def _do_map(state: ChunkMapState) -> dict:
        chunk_id: int = state["chunk_id"]
        source_id: int = state["source_id"]
        job_id: int | None = state.get("job_id")

        result = await services.map_chunks.map_single_chunk(
            chunk_id=chunk_id,
            source_id=source_id,
            job_id=job_id,
        )
        return {"map_result": result}

    graph.add_node("n_map_single", _do_map)
    graph.add_edge(START, "n_map_single")
    graph.add_edge("n_map_single", END)
    return graph.compile()


def make_process_chunk_node(services: RuntimeServices):
    """Return an async node function for use in the cognify graph (Send fan-out).

    Receives per-chunk state from ``Send("n_process_chunk", {...})``, calls
    ``map_single_chunk``, and returns a partial ``map_metrics`` update that
    the ``merge_dicts`` reducer accumulates into the cognify state.
    """
    if not services.map_chunks:
        raise ValueError("MapChunkService required for process_chunk node")

    async def process_chunk(state: dict) -> dict:
        chunk_id: int = state["chunk_id"]
        source_id: int = state["source_id"]
        job_id: int | None = state.get("job_id")

        try:
            result = await services.map_chunks.map_single_chunk(
                chunk_id=chunk_id,
                source_id=source_id,
                job_id=job_id,
            )
            return {"map_metrics": {str(chunk_id): result}}
        except Exception as exc:
            logger.warning("process_chunk failed for chunk %s: %s", chunk_id, exc)
            return {
                "map_metrics": {
                    str(chunk_id): {"error": str(exc), "entities_raw": 0, "relationships_raw": 0}
                }
            }

    return process_chunk
