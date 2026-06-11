"""POST /api/chat (+ session create + messages) handlers."""

from app.api import chat as chat_mod
from app.api.chat import ChatRequest, chat_endpoint, create_session_endpoint, messages_endpoint
from tests.conftest import run_async


def test_chat_endpoint_autocreates_session(monkeypatch):
    async def _fake_ask(self, session_id, message, k=8):
        return {"session_id": session_id, "answer": "ok", "citations": [], "bridge": []}

    monkeypatch.setattr(chat_mod.ChatService, "ask", _fake_ask)
    out = run_async(chat_endpoint(ChatRequest(message="hi")))
    assert out["answer"] == "ok"
    assert isinstance(out["session_id"], int)


def test_session_create_and_messages_roundtrip(monkeypatch):
    async def _fake_ask(self, session_id, message, k=8):
        await self._persist(session_id, message, "answer", [], [])
        return {"session_id": session_id, "answer": "answer", "citations": [], "bridge": []}

    monkeypatch.setattr(chat_mod.ChatService, "ask", _fake_ask)
    created = run_async(create_session_endpoint(title="t"))
    sid = created["session_id"]
    run_async(chat_endpoint(ChatRequest(message="hi", session_id=sid)))
    msgs = run_async(messages_endpoint(sid))
    assert msgs["session_id"] == sid
    assert len(msgs["messages"]) == 2


def test_chat_routes_registered():
    from app.main import app
    paths = {getattr(r, "path", None) for r in app.routes}
    assert "/api/chat" in paths
    assert "/api/chat/sessions" in paths
    assert "/api/chat/sessions/{session_id}/messages" in paths
