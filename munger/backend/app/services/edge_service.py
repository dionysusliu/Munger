"""Aggregate entity_relationships (evidence) into the derived entity_edges adjacency."""

from __future__ import annotations

from sqlalchemy import text

from app.core.config import Settings, get_settings
from app.core.database import async_session_maker

# Canonical-aware, undirected aggregation. COALESCE(canonical_entity_id, id) so this
# transparently collapses duplicates once SP2.2 resolution sets canonical ids.
_AGG_SELECT = """
    SELECT
        LEAST(s, t)  AS src_entity_id,
        GREATEST(s, t) AS tgt_entity_id,
        SUM(w)       AS weight,
        COUNT(*)     AS evidence_count,
        mode() WITHIN GROUP (ORDER BY rel) AS top_rel_type,
        now()        AS updated_at
    FROM (
        SELECT
            COALESCE(se.canonical_entity_id, er.source_entity_id) AS s,
            COALESCE(te.canonical_entity_id, er.target_entity_id) AS t,
            COALESCE(er.confidence, 1.0) AS w,
            er.relationship_type AS rel
        FROM entity_relationships er
        JOIN entities se ON se.id = er.source_entity_id
        JOIN entities te ON te.id = er.target_entity_id
    ) x
    WHERE s <> t
    GROUP BY LEAST(s, t), GREATEST(s, t)
"""

_INSERT_COLS = "(src_entity_id, tgt_entity_id, weight, evidence_count, top_rel_type, updated_at)"


class EdgeService:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()

    async def rebuild_all(self) -> int:
        """Full idempotent recompute of entity_edges from all evidence."""
        async with async_session_maker() as session:
            await session.execute(text("DELETE FROM entity_edges"))
            await session.execute(text(f"INSERT INTO entity_edges {_INSERT_COLS} {_AGG_SELECT}"))
            await session.commit()
            count = (await session.execute(text("SELECT count(*) FROM entity_edges"))).scalar()
        return int(count or 0)

    async def update_for_source(self, source_id: int) -> int:
        """Incrementally refresh only the canonical pairs touched by `source_id`.

        Each touched pair is recomputed from ALL evidence (not just this source) so
        the edge weight stays correct, then upserted. Bounded by the source's pairs.
        """
        touched_cte = """
            WITH touched AS (
                SELECT DISTINCT LEAST(s, t) AS src, GREATEST(s, t) AS tgt
                FROM (
                    SELECT COALESCE(se.canonical_entity_id, er.source_entity_id) AS s,
                           COALESCE(te.canonical_entity_id, er.target_entity_id) AS t
                    FROM entity_relationships er
                    JOIN entities se ON se.id = er.source_entity_id
                    JOIN entities te ON te.id = er.target_entity_id
                    WHERE er.source_id = :source_id
                ) y
                WHERE s <> t
            )
        """
        async with async_session_maker() as session:
            await session.execute(
                text(touched_cte + """
                    DELETE FROM entity_edges e
                    USING touched WHERE e.src_entity_id = touched.src AND e.tgt_entity_id = touched.tgt
                """),
                {"source_id": source_id},
            )
            await session.execute(
                text(touched_cte + f"""
                    INSERT INTO entity_edges {_INSERT_COLS}
                    SELECT agg.src_entity_id, agg.tgt_entity_id, agg.weight, agg.evidence_count, agg.top_rel_type, agg.updated_at
                    FROM ({_AGG_SELECT}) agg
                    JOIN touched ON touched.src = agg.src_entity_id AND touched.tgt = agg.tgt_entity_id
                """),
                {"source_id": source_id},
            )
            await session.commit()
            count = (await session.execute(text("SELECT count(*) FROM entity_edges"))).scalar()
        return int(count or 0)

    async def top_neighbors(self, entity_id: int, k: int = 20) -> list[dict]:
        """Top-k neighbors of `entity_id` by edge weight, across both stored directions."""
        sql = text("""
            SELECT CASE WHEN src_entity_id = :eid THEN tgt_entity_id ELSE src_entity_id END AS entity_id,
                   weight, evidence_count, top_rel_type
            FROM entity_edges
            WHERE src_entity_id = :eid OR tgt_entity_id = :eid
            ORDER BY weight DESC
            LIMIT :k
        """)
        async with async_session_maker() as session:
            rows = (await session.execute(sql, {"eid": entity_id, "k": k})).mappings().all()
        return [dict(r) for r in rows]
