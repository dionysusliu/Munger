"""POST /api/chat/stream SSE framing."""

import json

from app.api import chat as chat_mod
from app.api.chat import ChatRequest, chat_stream_endpoint
from tests.conftest import run_async


def test_stream_endpoint_frames_events(monkeypatch):
    async def _fake_ask_stream(self, session_id, message, k=8):
        yield {"type": "meta", "session_id": session_id, "citations": [], "bridge": []}
        yield {"type": "delta", "text": "hel"}
        yield {"type": "delta", "text": "lo"}
        yield {"type": "done", "assistant_message_id": 1, "answer": "hello"}

    monkeypatch.setattr(chat_mod.ChatService, "ask_stream", _fake_ask_stream)

    async def _collect():
        resp = await chat_stream_endpoint(ChatRequest(message="hi"))
        frames = []
        async for raw in resp.body_iterator:
            if isinstance(raw, bytes):
                raw = raw.decode()
            frames.append(raw)
        return resp, frames

    resp, frames = run_async(_collect())
    assert resp.media_type == "text/event-stream"
    events = [json.loads(f.removeprefix("data: ").strip()) for f in frames if f.strip()]
    types = [e["type"] for e in events]
    assert types == ["meta", "delta", "delta", "done"]
    assert events[0]["session_id"] >= 1  # session auto-created


def test_stream_route_registered():
    from app.main import app
    paths = {getattr(r, "path", None) for r in app.routes}
    assert "/api/chat/stream" in paths
