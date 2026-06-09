"""Build the parent ingest LangGraph graph: intake_subgraph → cognify_subgraph."""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from app.runtime.context import RuntimeServices
from app.runtime.graphs.cognify import build_cognify_subgraph
from app.runtime.graphs.intake import build_intake_subgraph
from app.runtime.graphs.state import IngestState


def _route_after_intake(state: IngestState) -> str:
    """Skip cognify when the source was flagged as a duplicate by n_hash_dedup."""
    return END if state.get("is_duplicate") else "cognify"


def build_ingest_graph(services: RuntimeServices, checkpointer=None):
    """Compile and return the parent ingest graph."""
    intake_subgraph = build_intake_subgraph(services)
    cognify_subgraph = build_cognify_subgraph(services)

    graph = StateGraph(IngestState)
    graph.add_node("intake", intake_subgraph)
    graph.add_node("cognify", cognify_subgraph)

    graph.add_edge(START, "intake")
    graph.add_conditional_edges("intake", _route_after_intake, ["cognify", END])
    graph.add_edge("cognify", END)

    compile_kwargs: dict = {}
    if checkpointer is not None:
        compile_kwargs["checkpointer"] = checkpointer

    return graph.compile(**compile_kwargs)
