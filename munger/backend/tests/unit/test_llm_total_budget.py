"""Total wall-clock ceilings on provider calls (nothing is allowed to run long).

Transport (httpx/openai) timeouts only bound gaps between bytes; a congested
provider trickling a response evades them — observed live: one wiki-page chat
call held a pipeline step for 15 minutes. These tests pin the hard total
budgets: `LLM_CALL_TIMEOUT_S` on chat/embed, 2x `LLM_STRUCTURED_TIMEOUT_S` on
the instructor exchange.
"""

import asyncio

import pytest

from app.core.config import Settings
from app.services.llm_service import LLMError, LLMService


def _settings(**overrides) -> Settings:
    return Settings(
        LLM_DEFAULT_PROVIDER="openrouter",
        LLM_DEFAULT_MODEL="deepseek/deepseek-v4-flash",
        LLM_EMBEDDING_MODEL="qwen/qwen3-embedding-8b",
        LLM_EMBEDDING_DIMENSIONS=768,
        OPENROUTER_API_KEY="test-key",
        **overrides,
    )


class _TrickleProvider:
    """Simulates a provider whose response never finishes."""

    async def chat(self, messages, **kwargs):
        await asyncio.sleep(30)
        return "too late"

    async def embed(self, texts):
        await asyncio.sleep(30)
        return [[0.0] * 768 for _ in texts]


class TestTotalCallBudget:
    def test_chat_exceeding_budget_raises(self):
        service = LLMService(_settings(LLM_CALL_TIMEOUT_S=0.05))
        service.provider = _TrickleProvider()
        with pytest.raises(LLMError, match="total budget"):
            asyncio.run(service.chat([{"role": "user", "content": "x"}]))

    def test_embed_exceeding_budget_raises(self):
        service = LLMService(_settings(LLM_CALL_TIMEOUT_S=0.05))
        service.provider = _TrickleProvider()
        with pytest.raises(LLMError, match="total budget"):
            asyncio.run(service.embed_texts(["x"]))

    def test_fast_calls_unaffected(self):
        class _Fast:
            async def chat(self, messages, **kwargs):
                return "ok"

            async def embed(self, texts):
                return [[0.0] * 768 for _ in texts]

        service = LLMService(_settings(LLM_CALL_TIMEOUT_S=5.0))
        service.provider = _Fast()
        assert asyncio.run(service.chat([{"role": "user", "content": "x"}])) == "ok"
        assert len(asyncio.run(service.embed_texts(["x"]))[0]) == 768
        assert service.stats["calls"] == 2

    def test_instructor_total_budget(self, monkeypatch):
        import instructor

        from pydantic import BaseModel

        class _Out(BaseModel):
            answer: str

        class _SlowCompletions:
            async def create(self, **kwargs):
                await asyncio.sleep(30)

        class _SlowClient:
            class chat:
                completions = _SlowCompletions()

        monkeypatch.setattr(instructor, "from_openai", lambda client, mode: _SlowClient())

        service = LLMService(
            _settings(LLM_STRUCTURED_TIMEOUT_S=0.05, INGEST_INSTRUCTOR_ENABLED=True)
        )
        with pytest.raises(LLMError, match="total budget"):
            asyncio.run(
                service._chat_structured_instructor(
                    [{"role": "user", "content": "x"}], _Out
                )
            )

    def test_default_budget_value(self):
        assert _settings().llm_call_timeout_s == 120.0
