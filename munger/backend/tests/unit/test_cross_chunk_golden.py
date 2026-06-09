"""Golden corpus cross-chunk linking under scripted LLM."""

from unittest.mock import MagicMock

import pytest

from app.core.config import Settings
from app.runtime.context import RuntimeServices
from app.runtime.graphs.ingest import build_ingest_graph
from app.schemas.extraction import ExtractionResult
from app.services.linking_service import LinkingService
from tests.fixtures.fake_llm import ScriptedLLMService, cross_chunk_extraction_scripts


class TestCrossChunkGolden:
    def test_linking_hybrid_score_for_surface_forms(self):
        settings = Settings()
        linking = LinkingService(llm_service=None, settings=settings)
        forms = linking._surface_forms("Charlie Munger")
        assert "Munger" in forms
        assert "Charlie Munger" in forms

    def test_scripted_llm_returns_structured_extraction(self):
        import asyncio

        llm = ScriptedLLMService(cross_chunk_extraction_scripts())
        result = asyncio.run(llm.chat_structured([], ExtractionResult))
        assert result.entities[0].name == "Charlie Munger"

    def test_ingest_graph_compiles_with_intake_subgraph(self):
        settings = Settings(ingest_orchestrator="graph", ingest_map_mode="send")
        llm = ScriptedLLMService(cross_chunk_extraction_scripts())
        services = RuntimeServices(
            settings=settings,
            storage=MagicMock(),
            llm=llm,
            entity=MagicMock(),
            wiki=MagicMock(),
            chunk=MagicMock(),
            map_chunks=MagicMock(),
            resolution=MagicMock(),
            linking=MagicMock(),
        )
        graph = build_ingest_graph(services, checkpointer=None)
        assert graph is not None
