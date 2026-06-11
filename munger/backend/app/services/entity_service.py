"""Entity service for extraction, deduplication, and linking of named entities."""

import json
import logging
from typing import Optional

from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.orm import selectinload

from app.core.database import async_session_maker
from app.core.config import get_settings
from app.models.entity import Entity, EntityMention
from app.models.wiki import WikiPage
from app.prompts import ALIAS_TYPE_MAPPING, ENTITY_TYPES, LEGACY_TYPE_MAPPING
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)


class EntityService:
    """Manages entity extraction, deduplication, and linking."""

    def __init__(self, llm_service: Optional[LLMService] = None):
        self.llm_service = llm_service

    # ------------------------------------------------------------------
    # Entity extraction
    # ------------------------------------------------------------------

    async def extract_from_text(self, text: str, source_id: int) -> list[Entity]:
        """Extract entities from text using LLM and persist them.

        Uses LLM for initial extraction, then deduplicates against existing
        entities in the database.
        """
        if not self.llm_service:
            logger.warning("No LLM service available for entity extraction")
            return []

        # Get LLM-extracted entities
        raw_entities = await self.llm_service.extract_entities(text)
        if not raw_entities:
            return []

        extracted = []
        for raw in raw_entities:
            name = raw.get("name", "").strip()
            entity_type = raw.get("type", "concept").lower().strip()
            description = raw.get("description", "").strip()

            if not name:
                continue

            # Normalize entity type
            entity_type = self._normalize_entity_type(entity_type)

            # Find or create entity
            entity = await self.find_or_create(
                name=name,
                entity_type=entity_type,
                description=description,
            )

            # Create mention
            await self._create_mention(entity.id, source_id, text)

            extracted.append(entity)

        logger.info(f"Extracted {len(extracted)} entities from source {source_id}")
        return extracted

    async def find_or_create(
        self,
        name: str,
        entity_type: str,
        description: Optional[str] = None,
        metadata_json: Optional[str] = None,
    ) -> Entity:
        """Find an existing entity by name (case-insensitive) or create a new one."""
        async with async_session_maker() as session:
            # Try exact match first
            result = await session.execute(
                select(Entity).where(
                    and_(
                        func.lower(Entity.name) == name.lower(),
                        Entity.entity_type == entity_type,
                    )
                )
            )
            existing = result.scalar_one_or_none()

            if existing:
                # Update mention count
                existing.mention_count += 1
                # Update description if it was empty
                if description and not existing.description:
                    existing.description = description
                await session.commit()
                return existing

            # Create new entity
            entity = Entity(
                name=name,
                entity_type=entity_type,
                description=description,
                metadata_json=metadata_json,
                mention_count=1,
            )
            session.add(entity)
            await session.commit()
            await session.refresh(entity)
            logger.debug(f"Created new entity: {name} ({entity_type})")
            return entity

    async def _create_mention(
        self,
        entity_id: int,
        source_id: int,
        context_text: str,
        mention_window: int = 200,
    ) -> EntityMention:
        """Create an entity mention record for a source."""
        async with async_session_maker() as session:
            # Extract a snippet of context around the entity
            context = context_text[:mention_window] if len(context_text) > mention_window else context_text

            mention = EntityMention(
                entity_id=entity_id,
                source_id=source_id,
                context=context,
            )
            session.add(mention)
            await session.commit()
            await session.refresh(mention)
            return mention

    # ------------------------------------------------------------------
    # Entity retrieval
    # ------------------------------------------------------------------

    async def get_entity(self, entity_id: int) -> Optional[Entity]:
        """Get an entity by ID with its wiki page."""
        async with async_session_maker() as session:
            result = await session.execute(
                select(Entity)
                .where(Entity.id == entity_id)
                .options(selectinload(Entity.wiki_page))
            )
            return result.scalar_one_or_none()

    async def get_entity_by_name(self, name: str) -> Optional[Entity]:
        """Get an entity by name (case-insensitive)."""
        async with async_session_maker() as session:
            result = await session.execute(
                select(Entity).where(func.lower(Entity.name) == name.lower())
            )
            return result.scalar_one_or_none()

    async def list_entities(
        self,
        entity_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Entity], int]:
        """List entities with optional type filter.

        Returns (entities, total_count).
        """
        async with async_session_maker() as session:
            query = select(Entity)
            count_query = select(func.count(Entity.id))

            if entity_type:
                query = query.where(Entity.entity_type == entity_type)
                count_query = count_query.where(Entity.entity_type == entity_type)

            # Order by mention count (most mentioned first)
            query = query.order_by(desc(Entity.mention_count))
            query = query.offset((page - 1) * page_size).limit(page_size)

            result = await session.execute(query)
            entities = result.scalars().all()

            count_result = await session.execute(count_query)
            total = count_result.scalar()

            return list(entities), total

    async def search_entities(self, query: str, entity_type: Optional[str] = None) -> list[Entity]:
        """Search entities by name or description."""
        async with async_session_maker() as session:
            search_term = f"%{query}%"
            db_query = select(Entity).where(
                or_(
                    Entity.name.ilike(search_term),
                    Entity.description.ilike(search_term),
                )
            )

            if entity_type:
                db_query = db_query.where(Entity.entity_type == entity_type)

            db_query = db_query.order_by(desc(Entity.mention_count)).limit(20)

            result = await session.execute(db_query)
            return list(result.scalars().all())

    # ------------------------------------------------------------------
    # Entity graph
    # ------------------------------------------------------------------

    async def get_entity_graph(self, entity_id: int) -> dict:
        """Get the full relationship graph for an entity.

        Returns a dict with nodes and edges for visualization.
        """
        entity = await self.get_entity(entity_id)
        if not entity:
            return {"nodes": [], "edges": []}

        nodes = [{"id": entity.id, "name": entity.name, "type": entity.entity_type}]
        edges = []

        # Get related entities
        related = await self.get_related_entities(entity_id, limit=20)
        for rel in related:
            nodes.append({
                "id": rel.id,
                "name": rel.name,
                "type": rel.entity_type,
            })
            edges.append({
                "from": entity.id,
                "to": rel.id,
            })

        return {"nodes": nodes, "edges": edges}

    async def get_related_entities(self, entity_id: int, limit: int = 10) -> list[Entity]:
        """Get entities related to the given entity through shared sources."""
        async with async_session_maker() as session:
            # Find entities that appear in the same sources
            subquery = (
                select(EntityMention.source_id)
                .where(EntityMention.entity_id == entity_id)
                .distinct()
            )

            result = await session.execute(
                select(Entity)
                .join(EntityMention, Entity.id == EntityMention.entity_id)
                .where(
                    and_(
                        EntityMention.source_id.in_(subquery),
                        Entity.id != entity_id,
                    )
                )
                .group_by(Entity.id)
                .order_by(desc(func.count(EntityMention.id)))
                .limit(limit)
            )
            return list(result.scalars().all())

    # ------------------------------------------------------------------
    # Entity-wiki linking
    # ------------------------------------------------------------------

    async def update_entity_wiki_page(
        self, entity_id: int, wiki_page_id: int
    ) -> Optional[Entity]:
        """Link an entity to a wiki page."""
        async with async_session_maker() as session:
            result = await session.execute(
                select(Entity).where(Entity.id == entity_id)
            )
            entity = result.scalar_one_or_none()

            if entity:
                entity.wiki_page_id = wiki_page_id
                await session.commit()
                await session.refresh(entity)
                logger.info(f"Linked entity {entity_id} to wiki page {wiki_page_id}")

            return entity

    async def get_entity_mentions(self, entity_id: int, page: int = 1, page_size: int = 20):
        """Get all mentions of an entity."""
        async with async_session_maker() as session:
            result = await session.execute(
                select(EntityMention)
                .where(EntityMention.entity_id == entity_id)
                .order_by(EntityMention.created_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
            mentions = result.scalars().all()

            count_result = await session.execute(
                select(func.count(EntityMention.id)).where(
                    EntityMention.entity_id == entity_id
                )
            )
            total = count_result.scalar()

            return list(mentions), total

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _normalize_entity_type(self, entity_type: str) -> str:
        """Normalize a raw LLM type label to the 7-type ontology vocabulary."""
        key = entity_type.lower().strip().replace(" ", "_")
        if key in ENTITY_TYPES:
            return key
        if key in LEGACY_TYPE_MAPPING:
            return LEGACY_TYPE_MAPPING[key]
        return ALIAS_TYPE_MAPPING.get(key, "concept")
