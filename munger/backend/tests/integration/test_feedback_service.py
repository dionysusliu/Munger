"""FeedbackService: merge/relate/rate — conservative HITL write-back."""

from sqlalchemy import text

from app.core.config import get_settings
from app.core.database import async_session_maker
from app.models.chat_message import ChatMessage
from app.models.chat_session import ChatSession
from app.models.entity import Entity
from app.services.feedback_service import FeedbackService
from tests.conftest import run_async


def _svc():
    return FeedbackService(get_settings())


async def _canon(eid):
    async with async_session_maker() as s:
        return (await s.execute(text("SELECT canonical_entity_id FROM entities WHERE id=:i"), {"i": eid})).scalar()


def _two(name_a="Acme Corp", name_b="Acme Corp.", t="organization"):
    async def _inner():
        async with async_session_maker() as s:
            a = Entity(name=name_a, entity_type=t, mention_count=5)
            b = Entity(name=name_b, entity_type=t, mention_count=1)
            s.add(a); s.add(b); await s.commit()
            return a.id, b.id
    return run_async(_inner())


def test_merge_feedback_same_forces_merge():
    a_id, b_id = _two("JPMorgan", "Chase Bank")
    out = run_async(_svc().merge_feedback(a_id, b_id, same=True))
    assert out["merged"] >= 1
    assert run_async(_canon(b_id)) == a_id


def test_merge_feedback_not_same_blocks():
    a_id, b_id = _two("Mercury", "Mercury", t="concept")
    run_async(_svc().merge_feedback(a_id, b_id, same=False))
    assert run_async(_canon(a_id)) is None and run_async(_canon(b_id)) is None


def test_relate_feedback_creates_edge_and_dedups():
    a_id, b_id = _two("Compounding", "Patience", t="concept")
    out1 = run_async(_svc().relate_feedback(a_id, b_id, note="user-asserted link"))
    out2 = run_async(_svc().relate_feedback(b_id, a_id))
    assert out1["created"] is True and out2["created"] is False

    async def _counts():
        async with async_session_maker() as s:
            rels = (await s.execute(text(
                "SELECT count(*) FROM entity_relationships WHERE method='human'"))).scalar()
            lo, hi = (a_id, b_id) if a_id < b_id else (b_id, a_id)
            edge = (await s.execute(text(
                "SELECT weight FROM entity_edges WHERE src_entity_id=:l AND tgt_entity_id=:h"),
                {"l": lo, "h": hi})).scalar()
            return rels, edge

    rels, edge_weight = run_async(_counts())
    assert rels == 1
    assert edge_weight is not None and edge_weight >= 1.0


def test_rate_message_assistant_only():
    async def _seed():
        async with async_session_maker() as s:
            sess = ChatSession(title="t"); s.add(sess); await s.flush()
            u = ChatMessage(session_id=sess.id, role="user", content="q")
            a = ChatMessage(session_id=sess.id, role="assistant", content="ans")
            s.add(u); s.add(a); await s.commit()
            return u.id, a.id

    u_id, a_id = run_async(_seed())
    assert run_async(_svc().rate_message(a_id, 1, "good bridge")) == 1
    assert run_async(_svc().rate_message(u_id, -1)) == 0
    assert run_async(_svc().rate_message(999999, 1)) == 0

    async def _row():
        async with async_session_maker() as s:
            return (await s.execute(text(
                "SELECT rating, feedback_note FROM chat_messages WHERE id=:i"), {"i": a_id})).first()

    rating, note = run_async(_row())
    assert rating == 1 and note == "good bridge"


def test_merge_feedback_reject_after_merge_undoes_it():
    """'Not the same' must also UNDO an existing soft-merge, not just flip the label."""
    a_id, b_id = _two("Alpha Co", "Alpha Co.")
    run_async(_svc().merge_feedback(a_id, b_id, same=True))
    assert run_async(_canon(b_id)) == a_id
    run_async(_svc().merge_feedback(a_id, b_id, same=False))
    assert run_async(_canon(b_id)) is None, "reject feedback must clear the existing merge"
    assert run_async(_canon(a_id)) is None
    # and it must STAY apart on a further resolve
    run_async(_svc().merge_feedback(a_id, b_id, same=False))
    assert run_async(_canon(b_id)) is None


def test_rate_message_rejects_invalid_rating():
    import pytest

    with pytest.raises(ValueError):
        run_async(_svc().rate_message(1, 0))
    with pytest.raises(ValueError):
        run_async(_svc().rate_message(1, 5))
