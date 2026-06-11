"""CommunityReportService: deterministic keywords + LLM summary + thematic search."""

from sqlalchemy import text

from app.core.config import get_settings
from app.core.database import async_session_maker
from app.models.community import Community
from app.models.entity import Entity
from app.services.community_report_service import CommunityReport, CommunityReportService
from tests.conftest import run_async
from tests.fixtures.fake_llm import ScriptedLLMService


def _seed_community(members):
    """members: list of (name, description, salience). Returns community_id."""
    async def _inner():
        async with async_session_maker() as s:
            c = Community(level=0, size=len(members))
            s.add(c); await s.flush()
            for name, desc, sal in members:
                s.add(Entity(name=name, entity_type="concept", description=desc,
                             salience=sal, community_id=c.id))
            await s.commit()
            return c.id
    return run_async(_inner())


def test_keywords_are_deterministic():
    svc = CommunityReportService(get_settings(), llm_service=ScriptedLLMService(scripts=[]))
    members = [("Compound Interest", "money grows on money over time", 0.9),
               ("Margin of Safety", "buy money assets below value", 0.5)]
    kws = svc._keywords(members, k=5)
    assert "money" in kws
    assert all(w == w.lower() for w in kws)


def test_generate_reports_writes_title_summary_keywords():
    cid = _seed_community([
        ("Compound Interest", "money grows on money", 0.9),
        ("Latticework", "mental models lattice", 0.7),
        ("Margin of Safety", "buy below intrinsic value", 0.5),
    ])
    llm = ScriptedLLMService(scripts=[{"title": "Munger Mental Models",
                                       "summary": "A cluster about compounding and decision frameworks."}])
    stats = run_async(CommunityReportService(get_settings(), llm_service=llm).generate_reports(min_size=3))
    assert stats["generated"] == 1

    async def _row():
        async with async_session_maker() as s:
            return (await s.execute(text(
                "SELECT title, summary, keywords, report_generated_at FROM communities WHERE id=:i"),
                {"i": cid})).first()

    title, summary, keywords, gen_at = run_async(_row())
    assert title == "Munger Mental Models"
    assert "compounding" in summary
    assert keywords
    assert gen_at is not None


def test_generate_reports_skips_small_communities():
    _seed_community([("Solo", "alone", 0.1)])
    llm = ScriptedLLMService(scripts=[{"title": "X", "summary": "Y"}])
    stats = run_async(CommunityReportService(get_settings(), llm_service=llm).generate_reports(min_size=3))
    assert stats["generated"] == 0


def test_community_search_matches_report_text():
    cid = _seed_community([
        ("Compound Interest", "money grows", 0.9),
        ("Latticework", "mental models", 0.7),
        ("Margin of Safety", "below value", 0.5),
    ])
    llm = ScriptedLLMService(scripts=[{"title": "Investing Principles",
                                       "summary": "Compounding and mental models for decisions."}])
    svc = CommunityReportService(get_settings(), llm_service=llm)
    run_async(svc.generate_reports(min_size=3))
    hits = run_async(svc.community_search("mental models"))
    assert any(h["community_id"] == cid for h in hits)
    assert hits[0]["title"] == "Investing Principles"
