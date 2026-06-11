"""Conservative HITL feedback write-back (SP4.2): merge / relate / rate.

Least-viable-state: each operation stores the human decision as irreducible evidence
(labeled_pairs row, method='human' relationship, message rating) and lets the existing
derivation machinery (resolve, edge rebuild) propagate it. Explicit user actions only —
never LLM-autonomous."""

from __future__ import annotations

from sqlalchemy import text

from app.core.config import Settings, get_settings
from app.core.database import async_session_maker
from app.services.edge_service import EdgeService
from app.services.entity_resolution_service import EntityResolutionService


class FeedbackService:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.resolution = EntityResolutionService(self.settings)
        self.edges = EdgeService(self.settings)

    async def merge_feedback(self, a_id: int, b_id: int, same: bool, note: str | None = None) -> dict:
        """'These two are (not) the same entity' -> labeled_pairs + resolve + edge rebuild."""
        label = "match" if same else "reject"
        await self.resolution.label_pair(a_id, b_id, label, note)
        stats = await self.resolution.resolve()
        await self.edges.rebuild_all()
        return {"label": label, **stats}

    async def relate_feedback(self, a_id: int, b_id: int,
                              relationship_type: str = "related", note: str | None = None) -> dict:
        """'X and Y are connected' -> method='human' relationship (dedup both directions) + edge rebuild.

        Dedup in the service: the quad-unique on entity_relationships does not fire for
        NULL source_id (Postgres treats NULLs as distinct).
        """
        if a_id == b_id:
            return {"created": False, "reason": "self-relation"}
        async with async_session_maker() as s:
            existing = (await s.execute(
                text("""
                    SELECT id FROM entity_relationships
                    WHERE method = 'human' AND relationship_type = :t AND source_id IS NULL
                      AND ((source_entity_id = :a AND target_entity_id = :b)
                        OR (source_entity_id = :b AND target_entity_id = :a))
                """),
                {"a": a_id, "b": b_id, "t": relationship_type},
            )).first()
            if existing:
                return {"created": False, "relationship_id": existing[0]}
            row = (await s.execute(
                text("""
                    INSERT INTO entity_relationships
                        (source_entity_id, target_entity_id, relationship_type, description,
                         confidence, method, created_at)
                    VALUES (:a, :b, :t, :d, 1.0, 'human', now())
                    RETURNING id
                """),
                {"a": a_id, "b": b_id, "t": relationship_type, "d": note},
            )).first()
            await s.commit()
        await self.edges.rebuild_all()
        return {"created": True, "relationship_id": row[0]}

    async def rate_message(self, message_id: int, rating: int, note: str | None = None) -> int:
        """Rate an ASSISTANT turn +1/-1 (stored signal; rank consumption deferred). Returns rows updated."""
        async with async_session_maker() as s:
            res = await s.execute(
                text("UPDATE chat_messages SET rating = :r, feedback_note = :n "
                     "WHERE id = :i AND role = 'assistant'"),
                {"r": rating, "n": note, "i": message_id},
            )
            await s.commit()
            return res.rowcount or 0
