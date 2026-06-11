"""Multi-session chat: list/delete sessions + auto-title from first message."""

from sqlalchemy import text

from app.api.chat import delete_session_endpoint, list_sessions_endpoint
from app.core.config import get_settings
from app.core.database import async_session_maker
from app.services.chat_service import ChatService
from app.services.graph_service import GraphService
from app.services.retrieval_service import RetrievalService
from tests.conftest import run_async
from tests.fixtures.fake_llm import ScriptedLLMService


def _svc(llm=None):
    llm = llm or ScriptedLLMService(scripts=["answer one", "answer two"])
    return ChatService(get_settings(), llm_service=llm,
                       retrieval=RetrievalService(get_settings(), llm_service=llm),
                       graph=GraphService(get_settings()))


def test_list_sessions_newest_first_with_counts():
    svc = _svc()
    s1 = run_async(svc.create_session("first"))
    s2 = run_async(svc.create_session(None))
    run_async(svc.ask(s2, "what is compounding?"))

    sessions = run_async(svc.list_sessions())
    ids = [s["id"] for s in sessions]
    assert ids.index(s2) < ids.index(s1)  # newest-first (s2 created later)
    by_id = {s["id"]: s for s in sessions}
    assert by_id[s1]["message_count"] == 0
    assert by_id[s2]["message_count"] == 2  # user + assistant
    assert {"id", "title", "created_at", "message_count", "last_message_at"} <= set(by_id[s1].keys())


def test_ask_autotitles_untitled_session():
    svc = _svc()
    sid = run_async(svc.create_session(None))
    run_async(svc.ask(sid, "tell me about the latticework of mental models please"))
    sessions = run_async(svc.list_sessions())
    title = next(s["title"] for s in sessions if s["id"] == sid)
    assert title and title.startswith("tell me about the latticework")
    assert len(title) <= 60

    # an explicit title is never overwritten
    sid2 = run_async(svc.create_session("my custom title"))
    run_async(svc.ask(sid2, "something else entirely"))
    sessions = run_async(svc.list_sessions())
    assert next(s["title"] for s in sessions if s["id"] == sid2) == "my custom title"


def test_delete_session_cascades_messages():
    svc = _svc()
    sid = run_async(svc.create_session("doomed"))
    run_async(svc.ask(sid, "hello"))
    assert run_async(svc.delete_session(sid)) is True
    assert run_async(svc.delete_session(sid)) is False  # already gone

    async def _counts():
        async with async_session_maker() as s:
            sess = (await s.execute(text("SELECT 1 FROM chat_sessions WHERE id=:i"), {"i": sid})).first()
            msgs = (await s.execute(text(
                "SELECT count(*) FROM chat_messages WHERE session_id=:i"), {"i": sid})).scalar()
            return sess, msgs

    sess, msgs = run_async(_counts())
    assert sess is None and msgs == 0


def test_session_endpoints_and_routes():
    out = run_async(list_sessions_endpoint())
    assert "sessions" in out

    svc = _svc()
    sid = run_async(svc.create_session("api-del"))
    deleted = run_async(delete_session_endpoint(sid))
    assert deleted["deleted"] is True

    from app.main import app
    routes = {(getattr(r, "path", None), tuple(sorted(getattr(r, "methods", []) or []))) for r in app.routes}
    paths = {p for p, _ in routes}
    assert "/api/chat/sessions" in paths  # POST (create) + GET (list)
    assert "/api/chat/sessions/{session_id}" in paths  # DELETE
