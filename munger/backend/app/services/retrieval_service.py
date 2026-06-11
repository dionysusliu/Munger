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

    @staticmethod
    def _rrf(ranked_lists: list[list[int]], k: int = RRF_K) -> dict[int, float]:
        scores: dict[int, float] = {}
        for lst in ranked_lists:
            for rank, eid in enumerate(lst):
                scores[eid] = scores.get(eid, 0.0) + 1.0 / (k + rank + 1)
        return scores

    async def _embed_query(self, query: str) -> list[float] | None:
        if self.llm is None:
            return None
        return await self.llm.embed_text(query)

    async def search(self, query: str, k: int = 20, salience_weight: float = 0.5) -> list[dict]:
        """Entity-centric retrieval: link -> recall(3) -> RRF -> salience rerank -> assemble top-k."""
        seeds = await self.link_seeds(query)
        qvec = await self._embed_query(query)

        vector_ids = await self._vector_entities(qvec) if qvec is not None else []
        lexical_ids = await self._lexical_entities(query)
        graph_ids = await self._graph_entities(seeds)

        fused = self._rrf([vector_ids, lexical_ids, graph_ids])
        if not fused:
            return []

        ids = list(fused.keys())
        async with async_session_maker() as s:
            sal_rows = (await s.execute(
                text("SELECT id, COALESCE(salience, 0.0) FROM entities WHERE id = ANY(:ids)"),
                {"ids": ids},
            )).all()
        salience = {r[0]: float(r[1]) for r in sal_rows}
        reranked = sorted(
            ids, key=lambda e: fused[e] * (1.0 + salience_weight * salience.get(e, 0.0)), reverse=True
        )[:k]

        return [await self._assemble(e, fused[e], salience.get(e, 0.0)) for e in reranked]

    async def _assemble(self, entity_id: int, score: float, salience: float) -> dict:
        async with async_session_maker() as s:
            ent = (await s.execute(
                text("SELECT id, name, entity_type, description, wiki_page_id, community_id "
                     "FROM entities WHERE id = :i"),
                {"i": entity_id},
            )).first()
            mentions = (await s.execute(
                text("SELECT source_id, chunk_id, context FROM entity_mentions "
                     "WHERE entity_id = :i AND context IS NOT NULL LIMIT 3"),
                {"i": entity_id},
            )).all()
            wiki = None
            if ent and ent[4] is not None:
                wiki = (await s.execute(
                    text("SELECT slug, title FROM wiki_pages WHERE id = :i"), {"i": ent[4]},
                )).first()
        neighbors = await self.edges.top_neighbors(entity_id, k=5)
        return {
            "entity_id": entity_id,
            "name": ent[1] if ent else None,
            "entity_type": ent[2] if ent else None,
            "description": ent[3] if ent else None,
            "community_id": ent[5] if ent else None,
            "score": score,
            "salience": salience,
            "wiki": {"slug": wiki[0], "title": wiki[1]} if wiki else None,
            "mentions": [{"source_id": m[0], "chunk_id": m[1], "context": m[2]} for m in mentions],
            "neighbors": neighbors,
        }
