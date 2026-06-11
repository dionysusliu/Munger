"""POST /api/communities/reports + GET /api/communities/search handlers."""

from sqlalchemy import text

from app.api.communities import reports_endpoint, search_endpoint
from app.core.database import async_session_maker
from app.models.community import Community
from app.models.entity import Entity
from app.services import community_report_service as crs
from tests.conftest import run_async


def _seed():
    async def _inner():
        async with async_session_maker() as s:
            c = Community(level=0, size=3)
            s.add(c); await s.flush()
            for n in ["Compound Interest", "Latticework", "Margin of Safety"]:
                s.add(Entity(name=n, entity_type="concept", description=n, salience=0.5, community_id=c.id))
            await s.commit()
            return c.id
    return run_async(_inner())


def test_reports_then_search_via_handlers(monkeypatch):
    cid = _seed()

    async def _fake_summarize(self, members):
        return crs.CommunityReport(title="Investing Principles", summary="Compounding and mental models.")

    # Patch the LLM step only; the endpoint still builds a real (lazy, no-network) LLMService.
    monkeypatch.setattr(crs.CommunityReportService, "_summarize", _fake_summarize)

    out = run_async(reports_endpoint(min_size=3))
    assert out["generated"] == 1
    hits = run_async(search_endpoint(q="mental models"))
    assert any(h["community_id"] == cid for h in hits["results"])


def test_communities_routes_registered():
    from app.main import app
    paths = {getattr(r, "path", None) for r in app.routes}
    assert "/api/communities/reports" in paths
    assert "/api/communities/search" in paths
