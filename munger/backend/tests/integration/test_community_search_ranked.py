"""SP3.3: community_search is FTS-ranked (ts_rank) with ILIKE substring fallback."""

from sqlalchemy import text

from app.core.config import get_settings
from app.core.database import async_session_maker
from app.services.community_report_service import CommunityReportService
from tests.conftest import run_async


def _seed_reported(title, summary, keywords, size):
    async def _inner():
        async with async_session_maker() as s:
            row = (await s.execute(text(
                "INSERT INTO communities (level, size, title, summary, keywords, report_generated_at, updated_at) "
                "VALUES (0, :sz, :t, :su, :k, now(), now()) RETURNING id"),
                {"sz": size, "t": title, "su": summary, "k": keywords})).first()
            await s.commit()
            return row[0]
    return run_async(_inner())


def _svc():
    return CommunityReportService(get_settings(), llm_service=None)


def test_search_vector_generated_column_populates():
    cid = _seed_reported("Queueing Theory", "analysis of queueing delay", "queueing,delay", 4)

    async def _vec():
        async with async_session_maker() as s:
            return (await s.execute(text(
                "SELECT search_vector IS NOT NULL FROM communities WHERE id=:i"), {"i": cid})).scalar()

    assert run_async(_vec()) is True


def test_fts_ranking_better_match_first():
    # smaller community but much denser match -> must outrank the bigger weak one
    strong = _seed_reported(
        "Queueing Delay Management",
        "Queueing theory governs queueing delay; managing queueing keeps delay bounded.",
        "queueing,delay,management", 3)
    weak = _seed_reported(
        "Network Infrastructure",
        "General networking topics; queueing and delay each appear once.",
        "network,infrastructure", 50)

    hits = run_async(_svc().community_search("queueing delay"))
    ids = [h["community_id"] for h in hits]
    assert strong in ids and weak in ids
    assert ids.index(strong) < ids.index(weak), "ts_rank must beat raw size ordering"


def test_substring_fallback_when_fts_misses():
    cid = _seed_reported("Self-Similar Traffic", "heavy-tailed distributions", "traffic", 5)
    # partial token: no FTS lexeme match, ILIKE substring still finds it
    hits = run_async(_svc().community_search("elf-Simila"))
    assert any(h["community_id"] == cid for h in hits)


def test_wildcard_still_escaped_in_fallback():
    _seed_reported("Anything", "whatever content", "stuff", 2)
    hits = run_async(_svc().community_search("%"))
    assert hits == []
