"""Per-community reports (LLM title+summary + deterministic keyword label) + thematic search.

The GraphRAG "global" layer: GraphService.recompute() produces communities; this derives a
human-readable report per community and exposes ILIKE thematic search over them. Reports are
regenerated after each recompute (recompute hard-deletes communities)."""

from __future__ import annotations

import logging
from collections import Counter

from pydantic import BaseModel
from sqlalchemy import text

from app.core.config import Settings, get_settings
from app.core.database import async_session_maker

logger = logging.getLogger(__name__)

_STOPWORDS = {
    "the", "a", "an", "of", "and", "to", "in", "is", "for", "on", "with", "by", "as", "at",
    "that", "this", "it", "from", "are", "be", "or", "its", "into", "over", "via", "their",
}


class CommunityReport(BaseModel):
    title: str
    summary: str


class CommunityReportService:
    def __init__(self, settings: Settings | None = None, llm_service=None):
        self.settings = settings or get_settings()
        self.llm = llm_service

    async def _members(self, community_id: int, limit: int) -> list[tuple[str, str, float]]:
        async with async_session_maker() as s:
            rows = (await s.execute(
                text("""
                    SELECT name, description, salience FROM entities
                    WHERE community_id = :c
                    ORDER BY salience DESC NULLS LAST
                    LIMIT :l
                """),
                {"c": community_id, "l": limit},
            )).all()
        return [(r[0], r[1] or "", float(r[2] or 0.0)) for r in rows]

    @staticmethod
    def _keywords(members: list[tuple[str, str, float]], k: int = 8) -> list[str]:
        cnt: Counter[str] = Counter()
        for name, desc, _ in members:
            for tok in f"{name} {desc}".lower().split():
                tok = tok.strip(".,;:()[]{}\"'`")
                if len(tok) > 2 and tok not in _STOPWORDS:
                    cnt[tok] += 1
        return [w for w, _ in cnt.most_common(k)]

    async def _summarize(self, members: list[tuple[str, str, float]]) -> CommunityReport:
        bullets = "\n".join(f"- {n}: {d[:160]}" for n, d, _ in members)
        messages = [
            {"role": "system", "content": (
                "You label a cluster of related entities from a knowledge graph. "
                "Return a concise title (<=6 words) and a 2-3 sentence summary of the theme that binds them."
            )},
            {"role": "user", "content": f"Entities in this community:\n{bullets}"},
        ]
        return await self.llm.chat_structured(messages, CommunityReport)

    async def generate_reports(self, min_size: int = 3, top_members: int = 15) -> dict:
        """(Re)generate title/summary/keywords for every community with size >= min_size."""
        async with async_session_maker() as s:
            comms = (await s.execute(
                text("SELECT id FROM communities WHERE size >= :m ORDER BY size DESC"),
                {"m": min_size},
            )).all()

        generated = 0
        for (cid,) in comms:
            try:
                members = await self._members(cid, top_members)
                if not members:
                    continue
                keywords = self._keywords(members)
                report = await self._summarize(members)
                async with async_session_maker() as s:
                    await s.execute(
                        text("""
                            UPDATE communities
                            SET title = :t, summary = :su, keywords = :k, report_generated_at = now()
                            WHERE id = :i
                        """),
                        {"t": report.title, "su": report.summary, "k": ",".join(keywords), "i": cid},
                    )
                    await s.commit()
                generated += 1
            except Exception as exc:  # one bad community must not abort the whole batch
                logger.warning("community %s report generation failed: %s", cid, exc)
        return {"communities": len(comms), "generated": generated}

    async def community_search(self, query: str, limit: int = 10) -> list[dict]:
        """Thematic search, ts_rank-ordered over the generated search_vector (SP3.3).

        websearch_to_tsquery semantics: multi-word queries are AND-matched after stemming
        (it never raises on malformed input). The escaped-ILIKE substring fallback fires
        only when FTS returns ZERO rows (partial tokens, non-English fragments) — a weak
        FTS hit intentionally wins over substring matches."""
        query = query[:200]  # belt: bound pathological input
        async with async_session_maker() as s:
            rows = (await s.execute(
                text("""
                    SELECT id, title, summary, size,
                           ts_rank(search_vector, websearch_to_tsquery('english', :q)) AS rank
                    FROM communities
                    WHERE search_vector @@ websearch_to_tsquery('english', :q)
                    ORDER BY rank DESC, size DESC
                    LIMIT :l
                """),
                {"q": query, "l": limit},
            )).all()
            if not rows:
                # escape LIKE wildcards (backslash is Postgres' default ESCAPE char)
                esc = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
                rows = (await s.execute(
                    text("""
                        SELECT id, title, summary, size, 0.0 AS rank FROM communities
                        WHERE title ILIKE :q OR summary ILIKE :q OR keywords ILIKE :q
                        ORDER BY size DESC
                        LIMIT :l
                    """),
                    {"q": f"%{esc}%", "l": limit},
                )).all()
        return [{"community_id": r[0], "title": r[1], "summary": r[2], "size": r[3]} for r in rows]
