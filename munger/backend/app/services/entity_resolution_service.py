"""Global, reversible entity resolution: block -> score -> cluster -> soft-merge via canonical_entity_id."""

from __future__ import annotations

import math

from rapidfuzz import fuzz
from sqlalchemy import text

from app.core.config import Settings, get_settings
from app.core.database import async_session_maker
from app.models.entity import Entity

W_NAME, W_EMB, W_NEIGHBOR = 0.5, 0.3, 0.2


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


class EntityResolutionService:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()

    async def _block_candidates(self, tau_block: float = 0.4, cap: int = 5000) -> list[tuple[int, int]]:
        """Candidate (a<b) pairs: same entity_type, both un-merged, name-trigram sim >= tau_block.

        Uses pg_trgm similarity() (not the % operator) to avoid %-escaping in text(); the GIN
        index is not used, so this is a per-pair scan within each entity_type block (MVP scale).
        """
        async with async_session_maker() as s:
            rows = (await s.execute(
                text("""
                    SELECT a.id, b.id
                    FROM entities a
                    JOIN entities b
                      ON a.entity_type = b.entity_type AND a.id < b.id
                    WHERE a.canonical_entity_id IS NULL AND b.canonical_entity_id IS NULL
                      AND similarity(a.name, b.name) >= :tau
                    ORDER BY similarity(a.name, b.name) DESC
                    LIMIT :cap
                """),
                {"tau": tau_block, "cap": cap},
            )).all()
        return [(r[0], r[1]) for r in rows]

    async def _load_adjacency(self) -> dict[int, set[int]]:
        adj: dict[int, set[int]] = {}
        async with async_session_maker() as s:
            rows = (await s.execute(
                text("SELECT src_entity_id, tgt_entity_id FROM entity_edges"))).all()
        for src, tgt in rows:
            adj.setdefault(src, set()).add(tgt)
            adj.setdefault(tgt, set()).add(src)
        return adj

    def _score_pair(self, a: Entity, b: Entity, adj: dict[int, set[int]]) -> float:
        parts: list[tuple[float, float]] = [(fuzz.token_set_ratio(a.name, b.name) / 100.0, W_NAME)]
        if a.embedding is not None and b.embedding is not None:
            parts.append((max(0.0, _cosine(list(a.embedding), list(b.embedding))), W_EMB))
        na, nb = adj.get(a.id, set()), adj.get(b.id, set())
        if na or nb:
            inter = len(na & nb)
            union = len(na | nb) or 1
            parts.append((inter / union, W_NEIGHBOR))
        total_w = sum(w for _, w in parts)
        return sum(v * w for v, w in parts) / total_w if total_w else 0.0

    async def score_ids(self, a_id: int, b_id: int) -> float:
        adj = await self._load_adjacency()
        async with async_session_maker() as s:
            a = await s.get(Entity, a_id)
            b = await s.get(Entity, b_id)
        return self._score_pair(a, b, adj)
