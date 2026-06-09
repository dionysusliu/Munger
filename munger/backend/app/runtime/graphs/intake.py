"""Build the ``intake`` LangGraph subgraph: register → parse → hash_dedup → (skip | done)."""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from app.runtime.context import RuntimeServices
from app.runtime.graphs.nodes.nodes_intake import is_duplicate, make_intake_nodes
from app.runtime.graphs.state import IntakeState


def build_intake_subgraph(services: RuntimeServices):
    """Compile and return the ``intake`` subgraph."""
    nodes = make_intake_nodes(services)

    graph = StateGraph(IntakeState)
    graph.add_node("n_register", nodes["n_register"])
    graph.add_node("n_parse", nodes["n_parse"])
    graph.add_node("n_hash_dedup", nodes["n_hash_dedup"])
    graph.add_node("n_skip", nodes["n_skip"])

    graph.add_edge(START, "n_register")
    graph.add_edge("n_register", "n_parse")
    graph.add_edge("n_parse", "n_hash_dedup")
    graph.add_conditional_edges("n_hash_dedup", is_duplicate, ["n_skip", END])
    graph.add_edge("n_skip", END)

    return graph.compile()


# Backward-compatible alias during migration
build_add_subgraph = build_intake_subgraph
