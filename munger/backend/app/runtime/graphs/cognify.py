"""Build the ``cognify`` LangGraph subgraph.

Send (parallel) mode::

    START → n_chunk → [fanout_chunks → Send("n_process_chunk", …) × N]
                                                 ↓
                   n_map_gate → (retry Send | n_reduce)
                   n_reduce → n_link → n_summarize → n_wiki → n_finalize → END

Service (legacy-gather) mode::

    START → n_chunk → n_map → n_map_gate → (retry n_map | n_reduce) → …

Toggle via ``settings.ingest_map_mode``:  ``"send"`` (default) | ``"service"``.
"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from app.runtime.context import RuntimeServices
from app.runtime.graphs.nodes.chunk_map import make_process_chunk_node
from app.runtime.graphs.nodes.nodes_cognify import make_cognify_nodes
from app.runtime.graphs.state import CognifyState


def build_cognify_subgraph(services: RuntimeServices):
    """Compile and return the ``cognify`` subgraph."""
    nodes = make_cognify_nodes(services)
    map_mode = (services.settings.ingest_map_mode or "send").lower()

    graph = StateGraph(CognifyState)

    graph.add_node("n_chunk", nodes["n_chunk"])
    graph.add_node("n_reduce", nodes["n_reduce"])
    graph.add_node("n_link", nodes["n_link"])
    graph.add_node("n_summarize", nodes["n_summarize"])
    graph.add_node("n_wiki", nodes["n_wiki"])
    graph.add_node("n_finalize", nodes["n_finalize"])

    graph.add_edge(START, "n_chunk")

    if map_mode == "send":
        # Parallel per-chunk fan-out via LangGraph Send
        graph.add_node("n_process_chunk", make_process_chunk_node(services))
        graph.add_node("n_map_gate", nodes["n_map_gate"])
        graph.add_conditional_edges(
            "n_chunk",
            nodes["fanout_chunks"],
            ["n_process_chunk", "n_map_gate"],
        )
        graph.add_edge("n_process_chunk", "n_map_gate")
        graph.add_conditional_edges(
            "n_map_gate",
            nodes["route_after_map_gate"],
            ["n_process_chunk", "n_reduce"],
        )
    else:
        # Legacy batched service gather
        graph.add_node("n_map", nodes["n_map"])
        graph.add_node("n_map_gate", nodes["n_map_gate"])
        graph.add_edge("n_chunk", "n_map")
        graph.add_edge("n_map", "n_map_gate")
        graph.add_conditional_edges(
            "n_map_gate",
            nodes["route_after_map_gate_service"],
            ["n_map", "n_reduce"],
        )

    graph.add_edge("n_reduce", "n_link")
    graph.add_edge("n_link", "n_summarize")
    graph.add_edge("n_summarize", "n_wiki")
    graph.add_edge("n_wiki", "n_finalize")
    graph.add_edge("n_finalize", END)

    return graph.compile()
