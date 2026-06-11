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
FEEDBACK_WEIGHT = 0.1  # per net-rating point (SP4.3 rating consumer)
FEEDBACK_CLAMP = 3     # net rating saturates at ±3 -> factor ∈ [0.7, 1.3]


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

    async def link_seeds(self, query: str, limit: int = 5, query_vec: list[float] | None = None) -> list[int]:
        """Seed entities (canonical) for the graph channel: name match + optional vector ANN (entities HNSW)."""
        tokens = [t for t in query.lower().split() if t]
        async with async_session_maker() as s:
            rows = (await s.execute(
                text("""
                    SELECT COALESCE(canonical_entity_id, id) AS cid, MAX(salience) AS sal
                    FROM entities
                    WHERE lower(name) = ANY(:tokens) OR name ILIKE :pat
                    GROUP BY COALESCE(canonical_entity_id, id)
                    ORDER BY sal DESC NULLS LAST
                    LIMIT :lim
                """),
                {"tokens": tokens or [""], "pat": f"%{query}%", "lim": limit},
            )).all()
            seeds: list[int] = [r[0] for r in rows]
            if query_vec is not None:
                vec_rows = (await s.execute(
                    text("""
                        SELECT COALESCE(canonical_entity_id, id) AS cid
                        FROM entities
                        WHERE embedding IS NOT NULL
                        ORDER BY embedding <=> CAST(:vec AS vector)
                        LIMIT :lim
                    """),
                    {"vec": _vec_literal(query_vec), "lim": limit},
                )).all()
                for (cid,) in vec_rows:
                    if cid not in seeds:
                        seeds.append(cid)
        return seeds

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

    async def _canonical_map(self, ids: list[int]) -> dict[int, int]:
        """id -> COALESCE(canonical_entity_id, id) for the given ids.

        Single COALESCE hop is correct because EntityResolutionService.resolve() runs
        _flatten_chains() — canonical_entity_id always points DIRECTLY to the root (no
        chains). Same invariant EdgeService._AGG_SELECT relies on.
        """
        uniq = list({i for i in ids})
        if not uniq:
            return {}
        async with async_session_maker() as s:
            rows = (await s.execute(
                text("SELECT id, COALESCE(canonical_entity_id, id) FROM entities WHERE id = ANY(:ids)"),
                {"ids": uniq},
            )).all()
        return {r[0]: r[1] for r in rows}

    @staticmethod
    def _collapse(ids: list[int], canon: dict[int, int]) -> list[int]:
        """Map each id to its canonical, dedup preserving first (best-rank) occurrence."""
        out: list[int] = []
        seen: set[int] = set()
        for i in ids:
            c = canon.get(i, i)
            if c not in seen:
                seen.add(c)
                out.append(c)
        return out

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

    async def _feedback_scores(self, ids: list[int]) -> dict[int, int]:
        """Net 👍/👎 per CANONICAL entity, summed over rated assistant turns citing it (SP4.3).

        Cited ids are resolved through COALESCE(canonical_entity_id, id) so ratings recorded
        before a merge still reach the canonical that rerank actually scores."""
        if not ids:
            return {}
        async with async_session_maker() as s:
            rows = (await s.execute(
                text("""
                    SELECT COALESCE(e.canonical_entity_id, e.id) AS eid, SUM(m.rating)::int AS net
                    FROM chat_messages m,
                         jsonb_array_elements((m.citations)::jsonb -> 'citations') AS c(value)
                    JOIN entities e ON e.id = (c.value ->> 'entity_id')::int
                    WHERE m.rating IS NOT NULL AND m.citations IS NOT NULL
                      AND COALESCE(e.canonical_entity_id, e.id) = ANY(:ids)
                    GROUP BY COALESCE(e.canonical_entity_id, e.id)
                """),
                {"ids": ids},
            )).all()
        return {r[0]: int(r[1]) for r in rows}

    @staticmethod
    def _feedback_factor(net: int) -> float:
        """Bounded rerank multiplier from net rating: 1 + 0.1*clamp(net, ±3) ∈ [0.7, 1.3].

        Conservative: feedback nudges close calls, never zeroes or dominates."""
        clamped = max(-FEEDBACK_CLAMP, min(FEEDBACK_CLAMP, net))
        return 1.0 + FEEDBACK_WEIGHT * clamped

    async def search(self, query: str, k: int = 20, salience_weight: float = 0.5) -> list[dict]:
        """Entity-centric retrieval: link -> recall(3) -> RRF -> salience rerank -> assemble top-k."""
        qvec = await self._embed_query(query)
        seeds = await self.link_seeds(query, query_vec=qvec)

        vector_ids = await self._vector_entities(qvec) if qvec is not None else []
        lexical_ids = await self._lexical_entities(query)
        graph_ids = await self._graph_entities(seeds)

        canon = await self._canonical_map(vector_ids + lexical_ids + graph_ids)
        vector_ids = self._collapse(vector_ids, canon)
        lexical_ids = self._collapse(lexical_ids, canon)
        graph_ids = self._collapse(graph_ids, canon)

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
        feedback = await self._feedback_scores(ids)
        reranked = sorted(
            ids,
            key=lambda e: fused[e]
            * (1.0 + salience_weight * salience.get(e, 0.0))
            * self._feedback_factor(feedback.get(e, 0)),
            reverse=True,
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
