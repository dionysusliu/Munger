"""Smoke tests for LangGraph ingest subgraph compilation."""

from unittest.mock import MagicMock

from app.core.config import Settings
from app.runtime.context import RuntimeServices
from app.runtime.graphs.intake import build_intake_subgraph
from app.runtime.graphs.cognify import build_cognify_subgraph
from app.runtime.graphs.ingest import build_ingest_graph
from app.runtime.pipeline_events import GRAPH_STEP_ORDER


class TestIngestGraphCompile:
    def test_graph_step_order_includes_link_entities(self):
        assert "register_source" in GRAPH_STEP_ORDER
        assert "hash_dedup" in GRAPH_STEP_ORDER
        assert "link_entities" in GRAPH_STEP_ORDER
        assert GRAPH_STEP_ORDER.index("link_entities") > GRAPH_STEP_ORDER.index("reduce_entities")

    def test_subgraphs_compile(self):
        settings = Settings(ingest_orchestrator="graph", ingest_map_mode="service")
        services = RuntimeServices(
            settings=settings,
            storage=MagicMock(),
            llm=MagicMock(),
            entity=MagicMock(),
            wiki=MagicMock(),
            chunk=MagicMock(),
            map_chunks=MagicMock(),
            resolution=MagicMock(),
            linking=MagicMock(),
        )
        from app.runtime.graphs.intake import build_intake_subgraph

        intake = build_intake_subgraph(services)
        cognify = build_cognify_subgraph(services)
        parent = build_ingest_graph(services, checkpointer=None)
        assert intake is not None
        assert cognify is not None
        assert parent is not None
        assert len(GRAPH_STEP_ORDER) == 11
