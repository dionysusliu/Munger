"""ChatService.ask: RAG synthesis + bridge + persistence (read-only)."""

from app.core.config import get_settings
from app.core.database import async_session_maker
from app.models.entity import Entity
from app.models.entity_edge import EntityEdge
from app.services.chat_service import ChatService
from app.services.graph_service import GraphService
from app.services.retrieval_service import RetrievalService
from tests.conftest import run_async
from tests.fixtures.fake_llm import ScriptedLLMService


def _svc(llm):
    return ChatService(get_settings(), llm_service=llm,
                       retrieval=RetrievalService(get_settings(), llm_service=llm),
                       graph=GraphService(get_settings()))


def _seed_two_linked():
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


def test_ask_synthesizes_with_citations_and_bridge_and_persists():
    a_id, b_id = _seed_two_linked()
    llm = ScriptedLLMService(scripts=["Compounding pairs with patience via discipline."])
    svc = _svc(llm)
    sid = run_async(svc.create_session("t"))
    out = run_async(svc.ask(sid, "tell me about compounding"))

    assert out["answer"].startswith("Compounding pairs")
    assert any(c["name"] == "Compounding" for c in out["citations"])
    assert a_id in out["bridge"] and b_id in out["bridge"]

    msgs = run_async(svc.messages(sid))
    assert len(msgs) == 2
    assert msgs[0]["role"] == "user" and msgs[1]["role"] == "assistant"
    assert msgs[1]["meta"] is not None


def test_history_is_replayed_into_prompt():
    _seed_two_linked()

    class _RecordingLLM(ScriptedLLMService):
        def __init__(self, scripts):
            super().__init__(scripts)
            self.last_messages = None

        async def chat(self, messages, **kwargs):
            self.last_messages = messages
            return await super().chat(messages, **kwargs)

    llm = _RecordingLLM(scripts=["first answer", "second answer"])
    svc = _svc(llm)
    sid = run_async(svc.create_session("t"))
    run_async(svc.ask(sid, "first question"))
    run_async(svc.ask(sid, "second question"))
    joined = " ".join(m["content"] for m in llm.last_messages)
    assert "first question" in joined and "first answer" in joined
