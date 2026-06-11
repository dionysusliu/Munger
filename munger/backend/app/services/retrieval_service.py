"""Entity-centric retrieval: link -> 3-channel recall -> RRF fuse -> salience rerank -> assemble.

Reuses the chunk-ANN + wiki-FTS SQL patterns from SearchService and the NetworkX graph
from GraphService. All-Postgres; no new migration (entity-embedding ANN is SP3.2).
"""

from __future__ import annotations

from sqlalchemy import text

from app.core.config import Settings, get_settings
from app.core.database import async_session_maker
from app.services.edge_service import EdgeService
from app.services.graph_service import GraphService

RRF_K = 60


def _vec_literal(vec: list[float]) -> str:
    return "[" + ",".join(repr(float(x)) for x in vec) + "]"


class RetrievalService:
    def __init__(self, settings: Settings | None = None, llm_service=None,
                 edge_service: EdgeService | None = None,
                 graph_service: GraphService | None = None):
        self.settings = settings or get_settings()
        self.llm = llm_service
        self.edges = edge_service or EdgeService(self.settings)
        self.graph = graph_service or GraphService(self.settings)

    async def link_seeds(self, query: str, limit: int = 5) -> list[int]:
        """Seed entities for the graph channel: exact lower(name) tokens OR ILIKE on the query."""
        tokens = [t for t in query.lower().split() if t]
        async with async_session_maker() as s:
            rows = (await s.execute(
                text("""
                    SELECT id FROM entities
                    WHERE lower(name) = ANY(:tokens) OR name ILIKE :pat
                    ORDER BY salience DESC NULLS LAST
                    LIMIT :lim
                """),
                {"tokens": tokens or [""], "pat": f"%{query}%", "lim": limit},
            )).all()
        return [r[0] for r in rows]

    async def _vector_entities(self, query_vec: list[float], limit: int = 20) -> list[int]:
        """Chunk ANN -> entity_mentions -> entity_ids, ranked by best (min) cosine distance."""
        async with async_session_maker() as s:
            rows = (await s.execute(
                text("""
                    SELECT em.entity_id, MIN(c.embedding <=> CAST(:vec AS vector)) AS dist
                    FROM chunks c
                    JOIN entity_mentions em ON em.chunk_id = c.id
                    WHERE c.embedding IS NOT NULL AND em.entity_id IS NOT NULL
                    GROUP BY em.entity_id
                    ORDER BY dist ASC
                    LIMIT :lim
                """),
                {"vec": _vec_literal(query_vec), "lim": limit},
            )).all()
        return [r[0] for r in rows]

    async def _lexical_entities(self, query: str, limit: int = 20) -> list[int]:
        """Wiki FTS -> entities via wiki_page_id, ranked by ts_rank."""
        async with async_session_maker() as s:
            rows = (await s.execute(
                text("""
                    SELECT e.id, ts_rank(w.search_vector, plainto_tsquery('english', :q)) AS rank
                    FROM wiki_pages w
                    JOIN entities e ON e.wiki_page_id = w.id
                    WHERE w.search_vector @@ plainto_tsquery('english', :q)
                    ORDER BY rank DESC
                    LIMIT :lim
                """),
                {"q": query, "lim": limit},
            )).all()
        return [r[0] for r in rows]

    async def _graph_entities(self, seeds: list[int], limit: int = 20) -> list[int]:
        """Personalized PageRank over entity_edges seeded by `seeds`, top entities by score."""
        if not seeds:
            return []
        scores = await self.graph.personalized_pagerank({s: 1.0 for s in seeds})
        ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
        return [eid for eid, _ in ranked[:limit]]
