"""Migration 012: chat_sessions + chat_messages tables."""

from sqlalchemy import text

from app.core.database import async_session_maker
from tests.conftest import run_async


def test_chat_tables_present():
    async def _inner():
        async with async_session_maker() as s:
            tabs = {
                r[0]
                for r in (await s.execute(text(
                    "SELECT table_name FROM information_schema.tables WHERE table_schema='public'"))).all()
            }
            cols = {
                r[0]
                for r in (await s.execute(text(
                    "SELECT column_name FROM information_schema.columns WHERE table_name='chat_messages'"))).all()
            }
            return tabs, cols

    tabs, cols = run_async(_inner())
    assert {"chat_sessions", "chat_messages"} <= tabs
    assert {"id", "session_id", "role", "content", "citations", "created_at"} <= cols
