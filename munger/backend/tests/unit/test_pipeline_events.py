"""Unit tests for pipeline step event helpers."""

from app.runtime.pipeline_events import (
    GRAPH_STEP_ORDER,
    INGEST_TOOL_ORDER,
    STEP_LABELS,
    canonical_tool_name,
    step_index,
)


class TestPipelineEvents:
    def test_canonical_tool_name_maps_aliases(self):
        assert canonical_tool_name("extract_source_text") == "parse_document"
        assert canonical_tool_name("create_wiki_pages") == "generate_wiki_pages"
        assert canonical_tool_name("extract_entities_from_text") == "map_chunks"
        assert canonical_tool_name("extract_entities_from_chunks") == "map_chunks"
        assert canonical_tool_name("resolve_entities") == "reduce_entities"

    def test_step_index_matches_graph_order(self):
        assert step_index("register_source") == 1
        assert step_index("parse_document") == 2
        assert step_index("link_entities") == 7
        assert step_index("finalize_ingest") == len(GRAPH_STEP_ORDER)

    def test_step_labels_cover_graph_steps(self):
        for tool in GRAPH_STEP_ORDER:
            assert tool in STEP_LABELS
            assert STEP_LABELS[tool]

    def test_step_labels_cover_legacy_agent_tools(self):
        for tool in INGEST_TOOL_ORDER:
            assert tool in STEP_LABELS
