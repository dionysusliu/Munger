"""Migration 010: labeled_pairs table exists with the expected columns + constraints."""

from sqlalchemy import text

from app.core.database import async_session_maker
from tests.conftest import run_async


def test_labeled_pairs_table_present():
    async def _inner():
        async with async_session_maker() as s:
            cols = {
                r[0]
                for r in (await s.execute(text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name='labeled_pairs'"))).all()
            }
            idx = {
                r[0]
                for r in (await s.execute(text(
                    "SELECT indexname FROM pg_indexes WHERE tablename='labeled_pairs'"))).all()
            }
            return cols, idx

    cols, idx = run_async(_inner())
    assert {"id", "entity_a_id", "entity_b_id", "label", "note", "created_at"} <= cols
    assert "uq_labeled_pairs_pair" in idx
