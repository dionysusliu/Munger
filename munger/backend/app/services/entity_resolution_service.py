"""Global, reversible entity resolution: block -> score -> cluster -> soft-merge via canonical_entity_id."""

from __future__ import annotations

import math

from rapidfuzz import fuzz
from sqlalchemy import select, text

from app.core.config import Settings, get_settings
from app.core.database import async_session_maker
from app.models.entity import Entity
from app.services.vector_store import VectorStore, get_vector_store

W_NAME, W_EMB, W_NEIGHBOR = 0.5, 0.3, 0.2


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


class EntityResolutionService:
    def __init__(self, settings: Settings | None = None, vector_store: VectorStore | None = None):
        self.settings = settings or get_settings()
        self.vectors = vector_store or get_vector_store(self.settings)

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

    def _score_pair(
        self, a: Entity, b: Entity, adj: dict[int, set[int]], vectors: dict[int, list[float]]
    ) -> float:
        parts: list[tuple[float, float]] = [(fuzz.token_set_ratio(a.name, b.name) / 100.0, W_NAME)]
        emb_a, emb_b = vectors.get(a.id), vectors.get(b.id)
        if emb_a is not None and emb_b is not None:
            # clamp anti-similarity (negative cosine) to 0 — treat as "no signal", not evidence against
            parts.append((max(0.0, _cosine(emb_a, emb_b)), W_EMB))
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
        if a is None or b is None:
            return 0.0
        vectors = await self.vectors.get_entity_vectors([a_id, b_id])
        return self._score_pair(a, b, adj, vectors)

    async def label_pair(self, a_id: int, b_id: int, label: str, note: str | None = None) -> None:
        """Record a HITL match/reject decision (ordered a<b, upsert)."""
        lo, hi = (a_id, b_id) if a_id < b_id else (b_id, a_id)
        async with async_session_maker() as s:
            await s.execute(
                text("""
                    INSERT INTO labeled_pairs (entity_a_id, entity_b_id, label, note)
                    VALUES (:a, :b, :label, :note)
                    ON CONFLICT (entity_a_id, entity_b_id)
                    DO UPDATE SET label = EXCLUDED.label, note = EXCLUDED.note
                """),
                {"a": lo, "b": hi, "label": label, "note": note},
            )
            await s.commit()

    async def _labels(self) -> tuple[set[tuple[int, int]], set[tuple[int, int]]]:
        async with async_session_maker() as s:
            rows = (await s.execute(text(
                "SELECT entity_a_id, entity_b_id, label FROM labeled_pairs"))).all()
        match = {(r[0], r[1]) for r in rows if r[2] == "match"}
        reject = {(r[0], r[1]) for r in rows if r[2] == "reject"}
        return match, reject

    async def resolve(self, tau_block: float = 0.4, tau_auto: float = 0.85) -> dict:
        """Block -> score -> apply labels -> cluster -> assign canonical_entity_id. Idempotent."""
        import networkx as nx

        candidates = await self._block_candidates(tau_block)
        match, reject = await self._labels()
        adj = await self._load_adjacency()

        def _ordered(p, q):
            return (p, q) if p < q else (q, p)

        ids = {e for pair in candidates for e in pair} | {e for pair in match for e in pair}
        ents: dict[int, Entity] = {}
        vectors: dict[int, list[float]] = {}
        if ids:
            async with async_session_maker() as s:
                ents = {
                    e.id: e
                    for e in (await s.execute(select(Entity).where(Entity.id.in_(list(ids))))).scalars().all()
                }
            # One batched vector fetch per scoring round (not per pair).
            vectors = await self.vectors.get_entity_vectors(list(ids))

        merge_edges: set[tuple[int, int]] = set()
        for a_id, b_id in candidates:
            key = _ordered(a_id, b_id)
            if key in reject:
                continue
            if (
                a_id in ents
                and b_id in ents
                and self._score_pair(ents[a_id], ents[b_id], adj, vectors) >= tau_auto
            ):
                merge_edges.add(key)
        for key in match:
            if key not in reject:
                merge_edges.add(key)

        g = nx.Graph()
        g.add_edges_from(merge_edges)
        merged = 0
        async with async_session_maker() as s:
            for comp in nx.connected_components(g):
                members = list(comp)
                meta = {
                    r[0]: (r[1] or 0, float(r[2] or 0.0))
                    for r in (await s.execute(text(
                        "SELECT id, mention_count, salience FROM entities WHERE id = ANY(:ids)"),
                        {"ids": members})).all()
                }
                canonical = max(members, key=lambda e: (meta[e][0], meta[e][1], -e))
                for m in members:
                    if m != canonical:
                        await s.execute(text(
                            "UPDATE entities SET canonical_entity_id = :c WHERE id = :m"),
                            {"c": canonical, "m": m})
                        merged += 1
            await s.commit()

        await self._flatten_chains()
        clusters = nx.number_connected_components(g) if g.number_of_nodes() else 0
        return {"candidates": len(candidates), "merged": merged, "clusters": clusters}

    async def _flatten_chains(self) -> None:
        """Collapse canonical_entity_id chains so every member points directly to its root.

        Cross-run merges can create B->A then A->D; EdgeService's single COALESCE hop would
        mis-resolve B. Re-point one hop at a time until no pointer targets another pointer.
        Terminates: a canonical always ranks above its members, so pointers form a cycle-free forest.
        """
        async with async_session_maker() as s:
            while True:
                res = await s.execute(text("""
                    UPDATE entities AS child
                    SET canonical_entity_id = parent.canonical_entity_id
                    FROM entities AS parent
                    WHERE child.canonical_entity_id = parent.id
                      AND parent.canonical_entity_id IS NOT NULL
                """))
                await s.commit()
                if not res.rowcount:
                    break

    async def unmerge(self, entity_id: int) -> int:
        """Reverse a soft-merge: clear this entity's pointer AND release any members pointing to it."""
        async with async_session_maker() as s:
            res = await s.execute(text(
                "UPDATE entities SET canonical_entity_id = NULL "
                "WHERE id = :e OR canonical_entity_id = :e"),
                {"e": entity_id})
            await s.commit()
            return res.rowcount or 0
