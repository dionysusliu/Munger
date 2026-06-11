"""POST /api/feedback/{merge,relate,rate} handlers."""

from sqlalchemy import text

from app.api.feedback import (
    MergeFeedback, RelateFeedback, RateFeedback,
    merge_endpoint, relate_endpoint, rate_endpoint,
)
from app.core.database import async_session_maker
from app.models.chat_message import ChatMessage
from app.models.chat_session import ChatSession
from app.models.entity import Entity
from tests.conftest import run_async


def test_merge_and_relate_endpoints():
    async def _setup():
        async with async_session_maker() as s:
            a = Entity(name="Tesla Inc", entity_type="organization", mention_count=9)
            b = Entity(name="Tesla Inc.", entity_type="organization", mention_count=1)
            s.add(a); s.add(b); await s.commit()
            return a.id, b.id

    a_id, b_id = run_async(_setup())
    out = run_async(merge_endpoint(MergeFeedback(entity_a_id=a_id, entity_b_id=b_id, same=True)))
    assert out["merged"] >= 1

    rel = run_async(relate_endpoint(RelateFeedback(entity_a_id=a_id, entity_b_id=b_id)))
    assert "created" in rel


def test_rate_endpoint():
    async def _seed():
        async with async_session_maker() as s:
            sess = ChatSession(title="t"); s.add(sess); await s.flush()
            m = ChatMessage(session_id=sess.id, role="assistant", content="ans")
            s.add(m); await s.commit()
            return m.id

    m_id = run_async(_seed())
    out = run_async(rate_endpoint(RateFeedback(message_id=m_id, rating=-1, note="off-topic")))
    assert out["updated"] == 1

    async def _val():
        async with async_session_maker() as s:
            return (await s.execute(text("SELECT rating FROM chat_messages WHERE id=:i"), {"i": m_id})).scalar()

    assert run_async(_val()) == -1


def test_feedback_routes_registered():
    from app.main import app
    paths = {getattr(r, "path", None) for r in app.routes}
    assert "/api/feedback/merge" in paths
    assert "/api/feedback/relate" in paths
    assert "/api/feedback/rate" in paths
