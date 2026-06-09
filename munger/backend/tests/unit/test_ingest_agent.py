"""Unit tests for ingest lead agent harness."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.runtime.agents.ingest_lead_agent import make_ingest_lead_agent
from app.runtime.context import RuntimeServices
from app.runtime.harness.skills.loader import load_skill
from app.runtime.pipeline_events import INGEST_TOOL_ORDER
from app.runtime.tools.ingest_tools import build_ingest_tools

BACKEND_ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS_DIR = str(BACKEND_ROOT / "data" / "workflows")

CORE_TOOLS = set(INGEST_TOOL_ORDER)
ALIAS_TOOLS = {"extract_source_text", "extract_entities_from_text", "create_wiki_pages"}


class TestIngestHarnessPieces:
    def test_build_ingest_tools_returns_eight_core_plus_deprecated_and_aliases(self):
        settings = MagicMock()
        settings.skills_dir = WORKFLOWS_DIR
        settings.builtin_skills_dir = WORKFLOWS_DIR
        services = RuntimeServices(
            settings=settings,
            storage=MagicMock(),
            llm=MagicMock(),
            entity=MagicMock(),
            wiki=MagicMock(),
        )
        tools = build_ingest_tools(services)
        names = {tool.name for tool in tools}
        assert CORE_TOOLS.issubset(names)
        assert ALIAS_TOOLS.issubset(names)
        assert "extract_entities_from_chunks" in names
        assert "map_chunks" in names
        assert "reduce_entities" in names

    def test_tools_accept_source_id_only_schema(self):
        settings = MagicMock()
        services = RuntimeServices(
            settings=settings,
            storage=MagicMock(),
            llm=MagicMock(),
            entity=MagicMock(),
            wiki=MagicMock(),
        )
        for tool in build_ingest_tools(services):
            schema = tool.args_schema.model_json_schema()
            props = set(schema.get("properties", {}).keys())
            assert props == {"source_id"}, f"{tool.name} schema must be source_id only"

    def test_load_ingest_skill_deerflow_format(self):
        settings = MagicMock()
        settings.skills_dir = WORKFLOWS_DIR
        settings.builtin_skills_dir = WORKFLOWS_DIR
        skill = load_skill(settings, "ingest")
        assert skill.name == "ingest"
        assert skill.allowed_tools is not None
        assert "parse_document" in skill.allowed_tools
        assert skill.tool_order is not None
        assert skill.tool_order[0] == "parse_document"

    def test_ingest_middleware_chain_has_four_layers(self):
        from app.runtime.harness.factory import build_ingest_middleware_chain

        chain = build_ingest_middleware_chain()
        assert len(chain) == 4

    def test_make_ingest_lead_agent_requires_llm(self):
        settings = MagicMock()
        settings.skills_dir = WORKFLOWS_DIR
        settings.builtin_skills_dir = WORKFLOWS_DIR
        services = RuntimeServices(
            settings=settings,
            storage=MagicMock(),
            llm=None,
            entity=MagicMock(),
            wiki=MagicMock(),
        )
        from langgraph.checkpoint.memory import InMemorySaver

        with pytest.raises(RuntimeError, match="LLM service is required"):
            make_ingest_lead_agent(services, InMemorySaver())
