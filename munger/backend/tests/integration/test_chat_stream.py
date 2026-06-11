"""ChatService.ask_stream: streaming meta/delta/done protocol + persistence (read-only)."""

import pytest

from app.core.config import get_settings
from app.core.database import async_session_maker
from app.models.entity import Entity
from app.models.entity_edge import EntityEdge
from app.services.chat_service import ChatService
from app.services.graph_service import GraphService
from app.services.llm_service import LLMProvider
from app.services.retrieval_service import RetrievalService
from tests.conftest import run_async
from tests.fixtures.fake_llm import ScriptedLLMService


def _svc(llm):
    return ChatService(
        get_settings(),
        llm_service=llm,
        retrieval=RetrievalService(get_settings(), llm_service=llm),
        graph=GraphService(get_settings()),
    )


def _seed_two_linked():
    """Seed two linked entities (mirrors test_chat_service._seed_two_linked)."""
    async def _inner():
        async with async_session_maker() as s:
            a = Entity(name="Compounding", entity_type="concept", description="growth on growth", salience=0.9)
            b = Entity(name="Patience", entity_type="concept", description="waiting", salience=0.5)
            s.add(a); s.add(b); await s.flush()
            lo, hi = (a.id, b.id) if a.id < b.id else (b.id, a.id)
            s.add(EntityEdge(src_entity_id=lo, tgt_entity_id=hi, weight=4.0, evidence_count=1))
            await s.commit()
            return a.id, b.id
    return run_async(_inner())


def test_ask_stream_event_sequence_and_persist():
    """ask_stream emits meta → delta* → done in order, and persists user + assistant rows."""
    _seed_two_linked()
    llm = ScriptedLLMService(scripts=["Compounding pairs with patience."])
    svc = _svc(llm)
    sid = run_async(svc.create_session("t"))

    events: list[dict] = []

    async def _collect():
        async for ev in svc.ask_stream(sid, "tell me about compounding"):
            events.append(ev)

    run_async(_collect())

    # First event must be meta
    assert events[0]["type"] == "meta"
    assert events[0]["session_id"] == sid
    assert "citations" in events[0]
    assert isinstance(events[0]["citations"], list)
    assert "bridge" in events[0]

    # At least 2 delta events
    deltas = [e for e in events if e["type"] == "delta"]
    assert len(deltas) >= 2, f"expected ≥2 deltas, got {len(deltas)}: {deltas}"

    # Last event is done with an int assistant_message_id
    assert events[-1]["type"] == "done"
    assert isinstance(events[-1]["assistant_message_id"], int)
    assert "answer" in events[-1]

    # Concatenated deltas must equal done.answer
    assert "".join(d["text"] for d in deltas) == events[-1]["answer"]

    # meta arrives BEFORE the first delta
    types = [e["type"] for e in events]
    meta_idx = types.index("meta")
    delta_idx = types.index("delta")
    assert meta_idx < delta_idx

    # Persistence: exactly 2 rows (user + assistant)
    msgs = run_async(svc.messages(sid))
    assert len(msgs) == 2
    assert msgs[0]["role"] == "user"
    assert msgs[1]["role"] == "assistant"
    assert msgs[1]["content"] == events[-1]["answer"]


def test_ask_stream_midstream_failure_persists_nothing():
    """If the LLM stream raises mid-way, ask_stream raises and persists nothing."""
    _seed_two_linked()

    class _FailingLLM(ScriptedLLMService):
        async def chat_stream(self, messages, **kwargs):  # type: ignore[override]
            yield "partial"
            raise RuntimeError("stream died")

    llm = _FailingLLM(scripts=[])
    svc = _svc(llm)
    sid = run_async(svc.create_session())

    async def _consume():
        async for _ in svc.ask_stream(sid, "test question"):
            pass

    with pytest.raises(RuntimeError, match="stream died"):
        run_async(_consume())

    # Nothing persisted
    msgs = run_async(svc.messages(sid))
    assert len(msgs) == 0


def test_base_provider_fallback_single_chunk():
    """LLMProvider.chat_stream base impl yields a single chunk from chat()."""

    class _MinimalProvider(LLMProvider):
        async def chat(self, messages, **kwargs) -> str:
            return "whole answer"

        async def embed(self, texts) -> list[list[float]]:
            return []

        @property
        def max_tokens(self) -> int:
            return 1024

    p = _MinimalProvider()

    async def _collect():
        chunks: list[str] = []
        async for chunk in p.chat_stream([]):
            chunks.append(chunk)
        return chunks

    chunks = run_async(_collect())
    assert len(chunks) == 1
    assert chunks[0] == "whole answer"
