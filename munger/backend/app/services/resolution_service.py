"""Merge chunk extractions into canonical entities and provenance mentions."""

from __future__ import annotations

import asyncio
import logging

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.core.config import Settings, get_settings
from app.core.database import async_session_maker
from app.models.chunk import Chunk
from app.models.chunk_extraction import ChunkExtraction
from app.models.entity import Entity, EntityMention
from app.models.source import Source
from app.models.entity_relationship import EntityRelationship
from app.services.entity_service import EntityService
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)

PROF_MERGE_SYSTEM = (
    "Merge these entity descriptions into one concise summary (max 512 chars). "
    "Preserve key facts from all sources."
)


class ResolutionService:
    def __init__(self, llm_service: LLMService | None = None, settings: Settings | None = None):
        self.llm = llm_service
        self.settings = settings or get_settings()
        self.entity_service = EntityService(llm_service=llm_service)

    @staticmethod
    def _lookup_entity_id(entity_names: dict[tuple[str, str], int], name: str) -> int | None:
        key = name.lower()
        for (n, _), eid in entity_names.items():
            if n == key:
                return eid
        return None

    async def _prof_merge_descriptions(self, descriptions: list[str]) -> str:
        unique = [d.strip() for d in descriptions if d and d.strip()]
        if not unique:
            return ""
        if len(unique) == 1:
            return unique[0]
        if not self.llm:
            return unique[0]
        combined = "\n---\n".join(unique)
        messages = [
            {"role": "system", "content": PROF_MERGE_SYSTEM},
            {"role": "user", "content": combined},
        ]
        try:
            return (await self.llm.chat(messages, max_tokens=512, temperature=0.1)).strip()
        except Exception as exc:
            logger.warning("Prof merge failed: %s", exc)
            return unique[0]

    async def _reconcile_global_description(self, existing: str, candidate: str) -> str:
        if not existing:
            return candidate
        if not candidate or existing == candidate:
            return existing
        # Keep global reconciliation deterministic during ingest retries; source-local
        # descriptions are already prof-merged before entity materialization.
        return existing if len(existing) >= len(candidate) else candidate

    async def reduce_entities(self, source_id: int) -> dict[str, int]:
        async with async_session_maker() as session:
            await session.execute(
                delete(EntityMention).where(EntityMention.source_id == source_id)
            )
            await session.execute(
                delete(EntityRelationship).where(EntityRelationship.source_id == source_id)
            )

            extractions = (
                await session.execute(
                    select(ChunkExtraction, Chunk)
                    .join(Chunk, Chunk.id == ChunkExtraction.chunk_id)
                    .where(ChunkExtraction.source_id == source_id)
                )
            ).all()

            descriptions_by_key: dict[tuple[str, str], list[str]] = {}
            raw_instances: list[tuple[dict, Chunk]] = []

            for extraction, chunk in extractions:
                for raw in extraction.entities or []:
                    name = (raw.get("name") or "").strip()
                    etype = (raw.get("type") or "concept").lower().strip()
                    if not name:
                        continue
                    etype = self.entity_service._normalize_entity_type(etype)
                    key = (name.lower(), etype)
                    desc = (raw.get("description") or "").strip()
                    descriptions_by_key.setdefault(key, [])
                    if desc:
                        descriptions_by_key[key].append(desc)
                    raw_instances.append((raw, chunk))

            prof_merges = 0
            merged_descriptions: dict[tuple[str, str], str] = {}
            keys_needing_merge = {
                k: v for k, v in descriptions_by_key.items() if len(v) > 1
            }
            sem = asyncio.Semaphore(self.settings.ingest_chunk_worker_concurrency)

            async def _merge_one(key: tuple[str, str], descs: list[str]) -> tuple[tuple[str, str], str]:
                async with sem:
                    merged = await self._prof_merge_descriptions(descs)
                return key, merged

            if keys_needing_merge:
                results = await asyncio.gather(
                    *[_merge_one(k, v) for k, v in keys_needing_merge.items()]
                )
                for key, merged in results:
                    merged_descriptions[key] = merged
                    prof_merges += 1

            for key, descs in descriptions_by_key.items():
                if key not in merged_descriptions and descs:
                    merged_descriptions[key] = descs[0]

            mention_count = 0
            entity_names: dict[tuple[str, str], int] = {}
            mention_keys: set[tuple[int, int]] = set()

            for raw, chunk in raw_instances:
                name = (raw.get("name") or "").strip()
                etype = (raw.get("type") or "concept").lower().strip()
                if not name:
                    continue
                etype = self.entity_service._normalize_entity_type(etype)
                key = (name.lower(), etype)
                candidate_desc = merged_descriptions.get(key, "")

                result = await session.execute(
                    select(Entity).where(
                        func.lower(Entity.name) == name.lower(),
                        Entity.entity_type == etype,
                    )
                )
                existing_entity = result.scalar_one_or_none()

                if existing_entity:
                    entity = existing_entity
                    if candidate_desc:
                        entity.description = await self._reconcile_global_description(
                            existing_entity.description or "",
                            candidate_desc,
                        )
                else:
                    entity = Entity(
                        name=name,
                        entity_type=etype,
                        description=candidate_desc or None,
                        mention_count=1,
                    )
                    session.add(entity)
                    await session.flush()

                entity_names[key] = entity.id

                pair_key = (entity.id, chunk.id)
                if pair_key in mention_keys:
                    continue
                mention_keys.add(pair_key)

                char_start = raw.get("char_start")
                char_end = raw.get("char_end")
                context = ""
                if char_start is not None and char_end is not None:
                    src = await session.get(Source, source_id)
                    if src and src.content_text:
                        context = src.content_text[int(char_start) : int(char_end)]

                session.add(
                    EntityMention(
                        entity_id=entity.id,
                        source_id=source_id,
                        chunk_id=chunk.id,
                        char_start=char_start,
                        char_end=char_end,
                        context=context or chunk.content[:200],
                        mention_method="extract",
                    )
                )
                entity.mention_count = (entity.mention_count or 0) + 1
                mention_count += 1

            for extraction, chunk in extractions:
                for rel in extraction.relationships or []:
                    src_name = (rel.get("source") or "").strip()
                    tgt_name = (rel.get("target") or "").strip()
                    rtype = (rel.get("type") or "relates_to").strip()
                    if not src_name or not tgt_name:
                        continue
                    src_id_ent = self._lookup_entity_id(entity_names, src_name)
                    tgt_id_ent = self._lookup_entity_id(entity_names, tgt_name)
                    if src_id_ent and tgt_id_ent:
                        stmt = pg_insert(EntityRelationship).values(
                            source_entity_id=src_id_ent,
                            target_entity_id=tgt_id_ent,
                            relationship_type=rtype,
                            description=rel.get("description"),
                            source_id=source_id,
                            chunk_id=chunk.id,
                        )
                        stmt = stmt.on_conflict_do_update(
                            index_elements=[
                                "source_entity_id",
                                "target_entity_id",
                                "relationship_type",
                                "source_id",
                            ],
                            set_={
                                "description": rel.get("description"),
                                "chunk_id": chunk.id,
                            },
                        )
                        await session.execute(stmt)

            await session.commit()

        return {
            "mentions_created": mention_count,
            "entities_canonical": len(entity_names),
            "prof_merges": prof_merges,
        }

    async def resolve_entities(self, source_id: int) -> dict[str, int]:
        result = await self.reduce_entities(source_id)
        return {
            "mentions_created": result["mentions_created"],
            "entities_canonical": result["entities_canonical"],
        }
