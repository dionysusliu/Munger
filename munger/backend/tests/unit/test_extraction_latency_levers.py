"""Latency levers in the extraction stage (ingest-latency workstream).

Measured 2026-06-12: a structured extraction window costs ~55 s because the
model emits ~10k chars of JSON at ~50 tok/s — latency scales with output
length. These tests pin the levers: the prompt's output budget, the reduced
max_tokens, and the per-stage model override.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.config import Settings
from app.services.extraction_service import EXTRACT_SYSTEM, GLEAN_SYSTEM, ExtractionService


def _settings(**overrides) -> Settings:
    return Settings(
        LLM_DEFAULT_PROVIDER="openrouter",
        LLM_DEFAULT_MODEL="deepseek/deepseek-v4-flash",
        LLM_EMBEDDING_MODEL="qwen/qwen3-embedding-8b",
        LLM_EMBEDDING_DIMENSIONS=768,
        OPENROUTER_API_KEY="test-key",
        **overrides,
    )


class TestOutputBudgetPrompt:
    def test_extract_system_carries_output_budget(self):
        assert "at most 20 words" in EXTRACT_SYSTEM
        assert "25 per chunk" in EXTRACT_SYSTEM
        assert "at most 12 words" in EXTRACT_SYSTEM

    def test_glean_system_carries_output_budget(self):
        assert "at most 20 words" in GLEAN_SYSTEM


class TestExtractionCallKwargs:
    def test_default_no_model_override_and_reduced_max_tokens(self):
        svc = ExtractionService(llm_service=MagicMock(), settings=_settings())
        kwargs = svc._call_kwargs()
        assert kwargs == {"max_tokens": 2048}

    def test_extraction_model_override_flows_to_kwargs(self):
        svc = ExtractionService(
            llm_service=MagicMock(),
            settings=_settings(LLM_EXTRACTION_MODEL="qwen/qwen3-30b-a3b-instruct-2507"),
        )
        kwargs = svc._call_kwargs()
        assert kwargs["model"] == "qwen/qwen3-30b-a3b-instruct-2507"
        assert kwargs["max_tokens"] == 2048

    def test_extract_chunk_passes_override_to_chat_structured(self):
        from app.schemas.extraction import ExtractionResult

        llm = MagicMock()
        llm.chat_structured = AsyncMock(return_value=ExtractionResult())
        svc = ExtractionService(
            llm_service=llm,
            settings=_settings(LLM_EXTRACTION_MODEL="qwen/qwen3-30b-a3b-instruct-2507"),
        )
        chunk = MagicMock()
        chunk.doc_char_start = 0
        chunk.content = "Alice met Bob."

        import asyncio

        asyncio.run(svc._extract_chunk(chunk, full_doc="Alice met Bob."))

        call_kwargs = llm.chat_structured.call_args.kwargs
        assert call_kwargs["model"] == "qwen/qwen3-30b-a3b-instruct-2507"
        assert call_kwargs["max_tokens"] == 2048


class TestStructuredTimeoutSetting:
    def test_default_is_60s(self):
        assert _settings().llm_structured_timeout_s == 60.0

    def test_env_alias(self):
        assert (
            _settings(LLM_STRUCTURED_TIMEOUT_S=45.0).llm_structured_timeout_s == 45.0
        )
