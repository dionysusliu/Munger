"""Migration 013: chat_messages has rating + feedback_note."""

from sqlalchemy import text

from app.core.database import async_session_maker
from tests.conftest import run_async


def test_chat_messages_feedback_columns_present():
    async def _inner():
        async with async_session_maker() as s:
            return {
                r[0]
                for r in (await s.execute(text(
                    "SELECT column_name FROM information_schema.columns WHERE table_name='chat_messages'"))).all()
            }

    cols = run_async(_inner())
    assert {"rating", "feedback_note"} <= cols
