"""Tests for per-pipeline-step LLM call/time telemetry (Task 3).

Two tests:
  test_pipeline_step_injects_llm_delta  — pipeline_step() with a dummy llm writes
      llm_calls/llm_ms into the pipeline_step_complete IngestEvent payload.
  test_real_llmservice_counters         — LLMService.stats increments correctly
      for chat() and embed_texts() (provider patched so no network is needed).
"""

from __future__ import annotations

import pytest
from sqlalchemy import select

from app.core.database import async_session_maker
from app.models.ingest_event import IngestEvent
from app.runtime.pipeline_events import pipeline_step
from tests.conftest import run_async


# ---------------------------------------------------------------------------
# Test 1: pipeline_step injects llm_calls / llm_ms into the complete event
# ---------------------------------------------------------------------------


class _DummyLLM:
    """Minimal llm stand-in that exposes a stats dict."""

    def __init__(self):
        self.stats: dict[str, int] = {"calls": 0, "ms": 0}


def test_pipeline_step_injects_llm_delta(create_source):
    """pipeline_step with llm= writes llm_calls/llm_ms into pipeline_step_complete.metrics."""
    source = create_source(title="Telemetry Pipeline Step Test")
    dummy = _DummyLLM()

    async def _run():
        async with pipeline_step(
            source_id=source.id,
            job_id=None,
            step_key="chunk_document",
            llm=dummy,
        ) as metrics:
            # Simulate 2 LLM calls happening during this step
            dummy.stats["calls"] += 2
            dummy.stats["ms"] += 150

    run_async(_run())

    # Fetch the pipeline_step_complete event from DB
    async def _fetch():
        async with async_session_maker() as session:
            result = await session.execute(
                select(IngestEvent)
                .where(IngestEvent.source_id == source.id)
                .where(IngestEvent.event_type == "pipeline_step_complete")
                .order_by(IngestEvent.id.desc())
                .limit(1)
            )
            return result.scalar_one_or_none()

    event = run_async(_fetch())
    assert event is not None, "pipeline_step_complete event must be recorded"

    m = event.payload.get("metrics", {})
    assert m.get("llm_calls") == 2, f"expected llm_calls=2, got {m}"
    assert m.get("llm_ms") == 150, f"expected llm_ms=150, got {m}"


# ---------------------------------------------------------------------------
# Test 2: LLMService.stats increments for chat() and embed_texts()
# ---------------------------------------------------------------------------


def test_real_llmservice_counters():
    """LLMService.stats accumulates calls and ms for chat() and embed_texts()."""
    from app.services.llm_service import LLMService
    from app.core.config import Settings

    # Settings picks up env vars set by conftest: ollama, unreachable port 9.
    settings = Settings()
    llm = LLMService(settings)

    # Patch provider calls so no network is required.
    async def _fake_chat(messages, **kwargs) -> str:
        return "x"

    async def _fake_embed(texts) -> list[list[float]]:
        return [[0.1] * 768 for _ in texts]

    llm.provider.chat = _fake_chat
    llm.provider.embed = _fake_embed

    async def _run():
        await llm.chat([{"role": "user", "content": "hello"}])
        await llm.chat([{"role": "user", "content": "world"}])
        await llm.embed_texts(["a sentence"])

    run_async(_run())

    assert llm.stats["calls"] == 3, f"expected 3 calls, got {llm.stats['calls']}"
    assert llm.stats["ms"] >= 0, "ms must be a non-negative integer"
