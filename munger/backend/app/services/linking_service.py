"""Cross-chunk entity linking: R-EMB entity embedding + co-mention relate links.

Full algorithm (plan §4): text-mention augmentation (R-TEXT), fuzzy/semantic hybrid
scoring (R-CAND/R-SCORE), merge application (R-MERGE), and relationship creation (R-LINK).
Requires migration 004_cross_chunk_linking (confidence + method columns on entity_relationships).
"""

from __future__ import annotations

import json
import logging
import re

from rapidfuzz import fuzz
from sqlalchemy import delete, select, text, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.core.config import Settings, get_settings
from app.core.database import async_session_maker
from app.models.entity import Entity, EntityMention
from app.models.entity_relationship import EntityRelationship
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)


class LinkingService:
    """Within-source cross-chunk entity linking.

    Invoked by the ``n_link`` graph node after ``reduce_entities``.  Populates
    ``entities.embedding`` (R-EMB), augments missed text mentions (R-TEXT), and
    creates ``entity_relationships`` rows for co-mentioned pairs (R-LINK).

    The full hybrid scoring ladder (fuzzy + pgvector semantic + LLM adjudication)
    is scaffolded below with TODO markers; the co-mention path is fully wired.
    """

    def __init__(
        self,
        llm_service: LLMService | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.llm = llm_service
        self.settings = settings or get_settings()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def link_source(
        self,
        source_id: int,
        *,
        job_id: int | None = None,
    ) -> dict[str, int]:
        """Run all linking stages for *source_id*.  Returns metrics dict."""
        async with async_session_maker() as session:
            result = await session.execute(
                select(Entity)
                .join(EntityMention, EntityMention.entity_id == Entity.id)
                .where(EntityMention.source_id == source_id)
                .distinct()
            )
            entities = list(result.scalars().unique().all())

        if not entities:
            return {"merges": 0, "cross_chunk_links": 0, "entity_embeddings": 0}

        entity_embeddings = await self._embed_entities(entities)
        await self._augment_text_mentions(source_id, entities)

        # Reload embeddings after persist
        async with async_session_maker() as session:
            entities = list(
                (
                    await session.execute(
                        select(Entity)
                        .join(EntityMention, EntityMention.entity_id == Entity.id)
                        .where(EntityMention.source_id == source_id)
                        .distinct()
                    )
                ).scalars().unique().all()
            )

        merges = await self._hybrid_merge(source_id, entities)
        cross_chunk_links = await self._link_by_co_mention(source_id, entities)

        return {
            "merges": merges,
            "cross_chunk_links": cross_chunk_links,
            "entity_embeddings": entity_embeddings,
        }

    # ------------------------------------------------------------------
    # Stage R-EMB: populate entities.embedding
    # ------------------------------------------------------------------

    async def _embed_entities(self, entities: list[Entity]) -> int:
        """Batch-embed ``"{name}: {description}"`` for each entity and persist."""
        if not self.llm:
            return 0

        texts = [
            f"{e.name}: {e.description}" if e.description else e.name
            for e in entities
        ]
        try:
            embeddings = await self.llm.embed_texts(texts)
        except Exception as exc:
            logger.warning("Entity embedding failed: %s", exc)
            return 0

        async with async_session_maker() as session:
            for entity, embedding in zip(entities, embeddings):
                await session.execute(
                    update(Entity)
                    .where(Entity.id == entity.id)
                    .values(embedding=embedding)
                )
            await session.commit()

        return len(entities)

    # ------------------------------------------------------------------
    # Stage R-TEXT: augment missed text mentions
    # ------------------------------------------------------------------

    async def _augment_text_mentions(
        self,
        source_id: int,
        entities: list[Entity],
    ) -> int:
        """Scan all chunks for entity surface-forms missed during extraction.

        Each new hit adds an EntityMention with ``context`` filled from the
        chunk text.  Skips if the (entity_id, chunk_id) pair already exists.
        """
        from app.models.chunk import Chunk

        async with async_session_maker() as session:
            result = await session.execute(
                select(Chunk)
                .where(Chunk.source_id == source_id)
                .order_by(Chunk.chunk_index)
            )
            chunks = list(result.scalars().all())

            existing_result = await session.execute(
                select(EntityMention.entity_id, EntityMention.chunk_id)
                .where(EntityMention.source_id == source_id)
            )
            existing_pairs: set[tuple[int, int]] = {
                (row.entity_id, row.chunk_id) for row in existing_result
            }

        added = 0
        pending_mentions: list[EntityMention] = []
        for entity in entities:
            surface_forms = self._surface_forms(entity.name)
            for chunk in chunks:
                if (entity.id, chunk.id) in existing_pairs:
                    continue
                text = chunk.content or ""
                for form in surface_forms:
                    pattern = re.compile(r"\b" + re.escape(form) + r"\b", re.IGNORECASE)
                    match = pattern.search(text)
                    if match:
                        pending_mentions.append(
                            EntityMention(
                                entity_id=entity.id,
                                source_id=source_id,
                                chunk_id=chunk.id,
                                char_start=match.start(),
                                char_end=match.end(),
                                context=text[max(0, match.start() - 50): match.end() + 50],
                                mention_method="link_text",
                            )
                        )
                        existing_pairs.add((entity.id, chunk.id))
                        added += 1
                        break

        if pending_mentions:
            async with async_session_maker() as session:
                for mention in pending_mentions:
                    session.add(mention)
                await session.commit()

        return added

    @staticmethod
    def _cosine(a: list[float], b: list[float]) -> float:
        if not a or not b or len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        na = sum(x * x for x in a) ** 0.5
        nb = sum(y * y for y in b) ** 0.5
        if na == 0 or nb == 0:
            return 0.0
        return dot / (na * nb)

    def _hybrid_score(self, a: Entity, b: Entity) -> float:
        lexical = fuzz.token_set_ratio(a.name, b.name) / 100.0
        emb_a = list(a.embedding) if a.embedding is not None else []
        emb_b = list(b.embedding) if b.embedding is not None else []
        semantic = self._cosine(emb_a, emb_b)
        return self.settings.link_w_lex * lexical + self.settings.link_w_sem * semantic

    async def _hybrid_merge(self, source_id: int, entities: list[Entity]) -> int:
        """Within-source fuzzy/semantic merge (v1 — no global destructive merge)."""
        merges = 0
        remaining = list(entities)
        i = 0
        while i < len(remaining):
            a = remaining[i]
            j = i + 1
            while j < len(remaining):
                b = remaining[j]
                if a.entity_type != b.entity_type:
                    j += 1
                    continue
                score = self._hybrid_score(a, b)
                if score >= self.settings.link_auto_merge:
                    winner, loser = (a, b) if (a.mention_count or 0) >= (b.mention_count or 0) else (b, a)
                    await self._apply_merge(winner.id, loser.id)
                    remaining = [e for e in remaining if e.id != loser.id]
                    merges += 1
                    break
                if self.settings.link_review_low <= score < self.settings.link_auto_merge:
                    if self.settings.link_llm_adjudicate and await self._llm_same_entity(a, b):
                        winner, loser = (a, b) if (a.mention_count or 0) >= (b.mention_count or 0) else (b, a)
                        await self._apply_merge(winner.id, loser.id)
                        remaining = [e for e in remaining if e.id != loser.id]
                        merges += 1
                        break
                j += 1
            else:
                i += 1
        return merges

    async def _llm_same_entity(self, a: Entity, b: Entity) -> bool:
        if not self.llm:
            return False
        messages = [
            {
                "role": "system",
                "content": 'Same real-world entity? JSON only: {"same": true|false}',
            },
            {
                "role": "user",
                "content": f"A: {a.name} ({a.entity_type})\nB: {b.name} ({b.entity_type})",
            },
        ]
        try:
            raw = await self.llm.chat(messages, max_tokens=32, temperature=0.0)
            return bool(json.loads(raw.strip()).get("same"))
        except Exception:
            return False

    async def _apply_merge(self, winner_id: int, loser_id: int) -> None:
        async with async_session_maker() as session:
            winner = await session.get(Entity, winner_id)
            loser = await session.get(Entity, loser_id)
            if not winner or not loser:
                return

            winner_chunk_ids = (
                await session.execute(
                    select(EntityMention.chunk_id).where(
                        EntityMention.entity_id == winner_id,
                        EntityMention.chunk_id.is_not(None),
                    )
                )
            ).scalars().all()
            if winner_chunk_ids:
                await session.execute(
                    delete(EntityMention).where(
                        EntityMention.entity_id == loser_id,
                        EntityMention.chunk_id.in_(winner_chunk_ids),
                    )
                )

            await session.execute(
                update(EntityMention)
                .where(EntityMention.entity_id == loser_id)
                .values(entity_id=winner_id)
            )
            await session.execute(
                text(
                    """
                    DELETE FROM entity_relationships er
                    WHERE er.source_entity_id = :loser_id
                      AND (
                        er.target_entity_id = :winner_id
                        OR EXISTS (
                            SELECT 1
                            FROM entity_relationships keep
                            WHERE keep.source_entity_id = :winner_id
                              AND keep.target_entity_id = er.target_entity_id
                              AND keep.relationship_type = er.relationship_type
                              AND keep.source_id IS NOT DISTINCT FROM er.source_id
                        )
                      )
                    """
                ),
                {"winner_id": winner_id, "loser_id": loser_id},
            )
            await session.execute(
                text(
                    """
                    DELETE FROM entity_relationships er
                    WHERE er.target_entity_id = :loser_id
                      AND (
                        er.source_entity_id = :winner_id
                        OR EXISTS (
                            SELECT 1
                            FROM entity_relationships keep
                            WHERE keep.source_entity_id = er.source_entity_id
                              AND keep.target_entity_id = :winner_id
                              AND keep.relationship_type = er.relationship_type
                              AND keep.source_id IS NOT DISTINCT FROM er.source_id
                        )
                      )
                    """
                ),
                {"winner_id": winner_id, "loser_id": loser_id},
            )
            await session.execute(
                update(EntityRelationship)
                .where(EntityRelationship.source_entity_id == loser_id)
                .values(source_entity_id=winner_id)
            )
            await session.execute(
                update(EntityRelationship)
                .where(EntityRelationship.target_entity_id == loser_id)
                .values(target_entity_id=winner_id)
            )
            winner.mention_count = (winner.mention_count or 0) + (loser.mention_count or 0)
            if loser.wiki_page_id and not winner.wiki_page_id:
                winner.wiki_page_id = loser.wiki_page_id
            # Bulk delete avoids ORM relationship synchronization trying to set
            # EntityMention.entity_id=NULL for loaded loser.mentions.
            await session.execute(delete(Entity).where(Entity.id == loser_id))
            await session.commit()

    # ------------------------------------------------------------------
    # Stage R-CAND + R-LINK: co-mention → related relationships
    # ------------------------------------------------------------------

    @staticmethod
    def _co_mention_pairs(
        chunk_entities: dict[int, set[int]],
        entity_chunks: dict[int, set[int]],
        *,
        min_cooccur: int,
        max_degree: int,
    ) -> dict[tuple[int, int], tuple[int, int]]:
        """Select meaningful co-mention pairs.

        Returns ``{(a, b): (weight, supporting_chunk)}`` for entity pairs that share at
        least ``min_cooccur`` chunks, keeping only each entity's top-``max_degree``
        partners by shared-chunk count. This replaces the previous all-pairs dump (one
        edge for any single shared chunk) that produced ~77k meaningless edges.
        """
        from collections import defaultdict

        candidates: set[tuple[int, int]] = set()
        for entity_ids in chunk_entities.values():
            lst = sorted(entity_ids)
            for i in range(len(lst)):
                for j in range(i + 1, len(lst)):
                    candidates.add((lst[i], lst[j]))

        weighted: list[tuple[int, int, int, int]] = []  # (weight, a, b, supporting_chunk)
        for a, b in candidates:
            shared = entity_chunks.get(a, set()) & entity_chunks.get(b, set())
            if len(shared) >= min_cooccur:
                weighted.append((len(shared), a, b, min(shared)))

        # Degree cap: keep an edge only if it is in BOTH endpoints' top-`max_degree`
        # partners (by weight). This strictly bounds every node's degree to max_degree,
        # so a hub entity cannot link to everything via low-degree partners.
        deg: dict[int, list[tuple[int, int]]] = defaultdict(list)
        for w, a, b, _ch in weighted:
            deg[a].append((w, b))
            deg[b].append((w, a))
        topn: dict[int, set[int]] = {}
        for node, edges in deg.items():
            edges.sort(key=lambda x: (-x[0], x[1]))
            topn[node] = {other for _w, other in edges[:max_degree]}

        result: dict[tuple[int, int], tuple[int, int]] = {}
        for w, a, b, ch in weighted:
            if b in topn.get(a, ()) and a in topn.get(b, ()):
                key = (a, b) if a < b else (b, a)
                result[key] = (w, ch)
        return result

    async def _link_by_co_mention(
        self,
        source_id: int,
        entities: list[Entity],
    ) -> int:
        """Create thresholded ``related`` EntityRelationship rows for co-mentioned pairs.

        A pair is kept only if both entities share ≥ ``ingest_link_min_cooccur`` chunks,
        bounded to each entity's top ``ingest_link_max_degree`` partners. Previous
        link-method relationships for this source are deleted first (idempotent).
        """
        link_methods = ("co_mention", "lexical", "semantic", "hybrid", "llm")

        async with async_session_maker() as session:
            await session.execute(
                delete(EntityRelationship).where(
                    EntityRelationship.source_id == source_id,
                    EntityRelationship.method.in_(link_methods),
                )
            )

            result = await session.execute(
                select(EntityMention.entity_id, EntityMention.chunk_id)
                .where(EntityMention.source_id == source_id)
            )
            rows = list(result.all())

            chunk_entities: dict[int, set[int]] = {}
            entity_chunks: dict[int, set[int]] = {}
            for row in rows:
                if row.chunk_id is None:
                    continue
                chunk_entities.setdefault(row.chunk_id, set()).add(row.entity_id)
                entity_chunks.setdefault(row.entity_id, set()).add(row.chunk_id)

            pairs = self._co_mention_pairs(
                chunk_entities,
                entity_chunks,
                min_cooccur=self.settings.ingest_link_min_cooccur,
                max_degree=self.settings.ingest_link_max_degree,
            )

            links_created = 0
            for (src_eid, tgt_eid), (weight, supporting_chunk) in pairs.items():
                stmt = pg_insert(EntityRelationship).values(
                    source_entity_id=src_eid,
                    target_entity_id=tgt_eid,
                    relationship_type="related",
                    method="co_mention",
                    confidence=0.6,
                    source_id=source_id,
                    chunk_id=supporting_chunk,
                    description=f"Co-mentioned in {weight} chunk(s)",
                )
                stmt = stmt.on_conflict_do_nothing(
                    index_elements=[
                        "source_entity_id",
                        "target_entity_id",
                        "relationship_type",
                        "source_id",
                    ]
                )
                await session.execute(stmt)
                links_created += 1
            await session.commit()

        return links_created

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _surface_forms(name: str) -> list[str]:
        """Generate surface variants: original name + last-word shortform."""
        forms = [name]
        parts = name.split()
        if len(parts) > 1:
            forms.append(parts[-1])
        return forms
