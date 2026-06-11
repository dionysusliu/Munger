"""Live LLM tests against a REAL provider (OpenRouter) — opt-in, never in the default run.

These exercise the LLM-dependent code paths with a real model instead of the scripted stub:
LLMService.chat / chat_structured / embed_text, and ChatService.ask end-to-end (real synthesis
over a seeded knowledge graph + the test DB).

Run them explicitly:

    OPENROUTER_API_KEY=sk-or-... \
    TEST_DATABASE_URL=postgresql+psycopg://munger_app:Munger.App.2026@localhost:5432/munger_test \
    .venv/bin/python -m pytest tests/live -m live_llm -v

Optional overrides: LIVE_CHAT_MODEL (default deepseek/deepseek-v4-flash), LIVE_EMBED_MODEL
(default qwen/qwen3-embedding-8b — must yield 768 dims to match the Vector(768) columns).
The defaults are the project's configured OpenRouter models (verified passing).

Default behavior: marked `integration` so pytest.ini's `addopts = -m "not integration"` DESELECTS
them from the normal suite; and each skips cleanly when OPENROUTER_API_KEY is unset. Transient
external failures (auth/rate-limit/connection/timeout) skip rather than fail.
"""

from __future__ import annotations

import os

import pytest
from pydantic import BaseModel

from app.core.config import Settings
from app.core.database import async_session_maker
from app.models.entity import Entity
from app.models.entity_edge import EntityEdge
from app.services.chat_service import ChatService
from app.services.graph_service import GraphService
from app.services.llm_service import LLMService
from app.services.retrieval_service import RetrievalService
from tests.conftest import run_async

pytestmark = [pytest.mark.integration, pytest.mark.live_llm]

_EXTERNAL_MARKERS = (
    "api key", "unauthorized", "forbidden", "rate limit", "rate-limit", "timeout", "timed out",
    "connection", "openrouter", "http 4", "http 5", "temporar", "quota", "insufficient", "overloaded",
)


def _skip_if_external(exc: Exception) -> None:
    """Skip (not fail) on a transient/external provider error; re-raise genuine code bugs."""
    msg = str(exc).lower()
    if any(m in msg for m in _EXTERNAL_MARKERS):
        pytest.skip(f"blocked external dependency: {exc}")
    raise exc


def _live_settings() -> Settings:
    key = os.getenv("OPENROUTER_API_KEY")
    if not key:
        pytest.skip("OPENROUTER_API_KEY not set — live LLM tests are opt-in")
    # Build our own Settings (conftest forces get_settings() to ollama; we must not use it here).
    return Settings(
        LLM_DEFAULT_PROVIDER="openrouter",
        OPENROUTER_API_KEY=key,
        LLM_DEFAULT_MODEL=os.getenv("LIVE_CHAT_MODEL", "deepseek/deepseek-v4-flash"),
        LLM_EMBEDDING_MODEL=os.getenv("LIVE_EMBED_MODEL", "qwen/qwen3-embedding-8b"),
        LLM_EMBEDDING_DIMENSIONS=768,
    )


@pytest.fixture
def live():
    settings = _live_settings()
    return settings, LLMService(settings)


def test_chat_returns_text(live):
    _settings, llm = live
    try:
        out = run_async(llm.chat(
            [{"role": "system", "content": "Reply with exactly one short sentence."},
             {"role": "user", "content": "Greet Charlie Munger."}],
            max_tokens=64,
        ))
    except Exception as exc:  # noqa: BLE001
        _skip_if_external(exc)
    assert isinstance(out, str) and out.strip()


def test_chat_structured_returns_model(live):
    _settings, llm = live

    class Reply(BaseModel):
        answer: str

    try:
        out = run_async(llm.chat_structured(
            [{"role": "system", "content": 'Return a JSON object {"answer": "..."} and nothing else.'},
             {"role": "user", "content": "What is two plus two?"}],
            Reply,
            max_tokens=64,
        ))
    except Exception as exc:  # noqa: BLE001
        _skip_if_external(exc)
    assert isinstance(out, Reply) and out.answer.strip()


def test_embed_text_is_768_dims(live):
    _settings, llm = live
    try:
        vec = run_async(llm.embed_text("compound interest and the latticework of mental models"))
    except Exception as exc:  # noqa: BLE001
        _skip_if_external(exc)
    assert isinstance(vec, list) and len(vec) == 768
    assert all(isinstance(x, float) for x in vec[:8])


def test_chat_service_ask_real_synthesis(live):
    settings, llm = live

    async def _seed():
        async with async_session_maker() as s:
            a = Entity(name="Compounding", entity_type="concept",
                       description="returns generating further returns over time", salience=0.9)
            b = Entity(name="Patience", entity_type="concept",
                       description="allowing time for compounding to work", salience=0.5)
            s.add(a); s.add(b); await s.flush()
            lo, hi = (a.id, b.id) if a.id < b.id else (b.id, a.id)
            s.add(EntityEdge(src_entity_id=lo, tgt_entity_id=hi, weight=4.0, evidence_count=1))
            await s.commit()
            return a.id, b.id

    _seed_ids = run_async(_seed())
    svc = ChatService(settings, llm_service=llm,
                      retrieval=RetrievalService(settings, llm_service=llm),
                      graph=GraphService(settings))
    sid = run_async(svc.create_session("live"))
    try:
        out = run_async(svc.ask(sid, "tell me about compounding"))
    except Exception as exc:  # noqa: BLE001
        _skip_if_external(exc)

    assert out["answer"].strip()  # a real, non-empty synthesized answer
    assert any(c["name"] == "Compounding" for c in out["citations"])  # grounded in retrieval
    msgs = run_async(svc.messages(sid))
    assert len(msgs) == 2 and msgs[0]["role"] == "user" and msgs[1]["role"] == "assistant"
