"""Entity API routes for Munger."""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.entity import Entity, EntityMention
from app.models.wiki import WikiPage
from app.schemas.entity import EntityCreate, EntityResponse, EntityList, EntityMentionResponse

router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _get_entity_or_404(db: AsyncSession, entity_id: int) -> Entity:
    entity = await db.get(Entity, entity_id)
    if not entity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entity not found")
    return entity


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("", response_model=EntityList)
async def list_entities(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    entity_type: Optional[str] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """List entities with pagination, optional type filter, and search."""
    query = select(Entity)
    count_query = select(func.count(Entity.id))

    if entity_type:
        query = query.where(Entity.entity_type == entity_type)
        count_query = count_query.where(Entity.entity_type == entity_type)

    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            Entity.name.ilike(search_pattern) | Entity.description.ilike(search_pattern)
        )
        count_query = count_query.where(
            Entity.name.ilike(search_pattern) | Entity.description.ilike(search_pattern)
        )

    query = query.order_by(desc(Entity.mention_count), Entity.name)

    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    result = await db.execute(query)
    entities = result.scalars().all()

    total_result = await db.execute(count_query)
    total = total_result.scalar()

    return EntityList(
        items=list(entities),
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{entity_id}", response_model=EntityResponse)
async def get_entity(
    entity_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get an entity by ID, including its associated wiki page info."""
    entity = await _get_entity_or_404(db, entity_id)
    return entity


@router.get("/{entity_id}/mentions")
async def get_entity_mentions(
    entity_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Get all mentions of an entity.

    Returns paginated mentions with context about where the entity appears.
    """
    entity = await _get_entity_or_404(db, entity_id)

    # Count total mentions
    count_result = await db.execute(
        select(func.count(EntityMention.id)).where(EntityMention.entity_id == entity_id)
    )
    total = count_result.scalar()

    # Get mentions with source/wiki page titles
    offset = (page - 1) * page_size
    result = await db.execute(
        select(EntityMention)
        .where(EntityMention.entity_id == entity_id)
        .order_by(desc(EntityMention.created_at))
        .offset(offset)
        .limit(page_size)
    )

    mentions = []
    for mention in result.scalars().all():
        mentions.append({
            "id": mention.id,
            "entity_id": mention.entity_id,
            "entity_name": entity.name,
            "source_id": mention.source_id,
            "wiki_page_id": mention.wiki_page_id,
            "chunk_id": mention.chunk_id,
            "char_start": mention.char_start,
            "char_end": mention.char_end,
            "context": mention.context,
            "created_at": mention.created_at,
        })

    return {
        "entity_id": entity_id,
        "entity_name": entity.name,
        "total_mentions": total,
        "page": page,
        "page_size": page_size,
        "mentions": mentions,
    }


@router.get("/{entity_id}/provenance")
async def get_entity_provenance(
    entity_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Return source → chunk → excerpt provenance chain for an entity."""
    await _get_entity_or_404(db, entity_id)
    from app.services.provenance_service import ProvenanceService

    chain = await ProvenanceService().get_provenance_chain(entity_id)
    return {"entity_id": entity_id, "provenance": chain}


@router.get("/{entity_id}/related")
async def get_related_entities(
    entity_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get related entities.

    Related entities are found by:
    1. Co-occurrence in the same sources/wiki pages
    2. Sharing the same entity type
    3. Having wiki pages that link to each other
    """
    entity = await _get_entity_or_404(db, entity_id)

    # Find source_ids and wiki_page_ids where this entity is mentioned
    mention_result = await db.execute(
        select(EntityMention.source_id, EntityMention.wiki_page_id)
        .where(EntityMention.entity_id == entity_id)
    )

    source_ids = set()
    wiki_page_ids = set()
    for row in mention_result.all():
        sid, wid = row
        if sid:
            source_ids.add(sid)
        if wid:
            wiki_page_ids.add(wid)

    related_ids = set()

    # Find other entities mentioned in the same sources
    if source_ids:
        result = await db.execute(
            select(EntityMention.entity_id)
            .where(EntityMention.source_id.in_(list(source_ids)))
            .where(EntityMention.entity_id != entity_id)
        )
        for row in result.all():
            related_ids.add(row[0])

    # Find other entities mentioned in the same wiki pages
    if wiki_page_ids:
        result = await db.execute(
            select(EntityMention.entity_id)
            .where(EntityMention.wiki_page_id.in_(list(wiki_page_ids)))
            .where(EntityMention.entity_id != entity_id)
        )
        for row in result.all():
            related_ids.add(row[0])

    if not related_ids:
        return {"entity_id": entity_id, "related_entities": []}

    # Fetch related entities
    result = await db.execute(
        select(Entity)
        .where(Entity.id.in_(list(related_ids)))
        .order_by(desc(Entity.mention_count))
        .limit(20)
    )
    related = result.scalars().all()

    return {
        "entity_id": entity_id,
        "entity_name": entity.name,
        "related_entities": [
            {
                "id": e.id,
                "name": e.name,
                "entity_type": e.entity_type,
                "mention_count": e.mention_count,
                "description": e.description,
            }
            for e in related
        ],
    }


@router.put("/{entity_id}", response_model=EntityResponse)
async def update_entity(
    entity_id: int,
    data: EntityCreate,
    db: AsyncSession = Depends(get_db),
):
    """Update an entity (manual edit).

    Allows updating name, type, description, wiki page association, and metadata.
    """
    entity = await _get_entity_or_404(db, entity_id)

    entity.name = data.name
    entity.entity_type = data.entity_type
    entity.description = data.description
    entity.wiki_page_id = data.wiki_page_id
    entity.metadata_json = data.metadata_json
    entity.updated_at = datetime.now(timezone.utc)

    await db.flush()
    await db.refresh(entity)

    return entity
