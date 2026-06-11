"""Migration 011: communities has report columns."""

from sqlalchemy import text

from app.core.database import async_session_maker
from tests.conftest import run_async


def test_communities_report_columns_present():
    async def _inner():
        async with async_session_maker() as s:
            return {
                r[0]
                for r in (await s.execute(text(
                    "SELECT column_name FROM information_schema.columns WHERE table_name='communities'"))).all()
            }

    cols = run_async(_inner())
    assert {"title", "summary", "keywords", "report_generated_at"} <= cols
