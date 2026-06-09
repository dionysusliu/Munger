"""Search API routes for Munger."""
import time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.wiki import WikiPage
from app.models.source import Source
from app.models.entity import Entity
from app.schemas.search import SearchResponse, SearchResult

router = APIRouter()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("")
async def search(
    q: str = Query(..., min_length=1, description="Search query"),
    result_type: str = Query("all", description="Filter by type: all, wiki_page, source, entity"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> SearchResponse:
    """Full-text search across wiki pages, sources, and entities.

    Performs a case-insensitive LIKE search on titles, content, and names.
    Results are returned in order of relevance (title match > content match).

    For semantic search, use ``/api/search/semantic``.
    """
    start_time = time.time()

    if not q or not q.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    query = q.strip()
    search_pattern = f"%{query}%"
    results: list[SearchResult] = []

    # Search wiki pages
    if result_type in ("all", "wiki_page"):
        wiki_result = await db.execute(
            select(WikiPage)
            .where(
                or_(
                    WikiPage.title.ilike(search_pattern),
                    WikiPage.content.ilike(search_pattern),
                    WikiPage.slug.ilike(search_pattern),
                )
            )
            .order_by(
                desc(WikiPage.title.ilike(search_pattern)),
                desc(WikiPage.updated_at),
            )
            .limit(page_size)
        )
        wiki_pages = wiki_result.scalars().all()

        for wp in wiki_pages:
            # Calculate a simple relevance score
            score = 1.0
            if query.lower() in wp.title.lower():
                score = 2.0
            if query.lower() == wp.title.lower():
                score = 3.0

            # Get content snippet
            content_snippet = wp.content[:300] + "..." if len(wp.content) > 300 else wp.content

            results.append(SearchResult(
                id=wp.id,
                title=wp.title,
                content=content_snippet,
                result_type="wiki_page",
                score=score,
                slug=wp.slug,
                page_type=wp.page_type,
            ))

    # Search sources
    if result_type in ("all", "source"):
        source_result = await db.execute(
            select(Source)
            .where(
                or_(
                    Source.title.ilike(search_pattern),
                    Source.content_text.ilike(search_pattern),
                    Source.content_summary.ilike(search_pattern),
                    Source.filename.ilike(search_pattern),
                )
            )
            .order_by(
                desc(Source.title.ilike(search_pattern)),
                desc(Source.created_at),
            )
            .limit(page_size)
        )
        sources = source_result.scalars().all()

        for src in sources:
            score = 1.0
            if query.lower() in src.title.lower():
                score = 2.0

            content_snippet = ""
            if src.content_summary:
                content_snippet = src.content_summary[:300]
            elif src.content_text:
                content_snippet = src.content_text[:300]
            if len(content_snippet) > 300:
                content_snippet = content_snippet[:300] + "..."

            results.append(SearchResult(
                id=src.id,
                title=src.title,
                content=content_snippet or src.filename,
                result_type="source",
                score=score,
            ))

    # Search entities
    if result_type in ("all", "entity"):
        entity_result = await db.execute(
            select(Entity)
            .where(
                or_(
                    Entity.name.ilike(search_pattern),
                    Entity.description.ilike(search_pattern),
                )
            )
            .order_by(
                desc(Entity.name.ilike(search_pattern)),
                desc(Entity.mention_count),
            )
            .limit(page_size)
        )
        entities = entity_result.scalars().all()

        for ent in entities:
            score = 1.0
            if query.lower() in ent.name.lower():
                score = 2.0
            if query.lower() == ent.name.lower():
                score = 3.0

            results.append(SearchResult(
                id=ent.id,
                title=ent.name,
                content=ent.description or "" if ent.description else f"Type: {ent.entity_type}",
                result_type="entity",
                score=score,
                entity_type=ent.entity_type,
            ))

    # Sort results by score (highest first)
    results.sort(key=lambda r: r.score, reverse=True)

    # Pagination
    total = len(results)
    start = (page - 1) * page_size
    end = start + page_size
    paginated_results = results[start:end]

    execution_time_ms = (time.time() - start_time) * 1000

    return SearchResponse(
        query=query,
        results=paginated_results,
        total=total,
        page=page,
        page_size=page_size,
        execution_time_ms=round(execution_time_ms, 2),
    )


@router.get("/semantic")
async def search_semantic(
    q: str = Query(..., min_length=1, description="Search query for semantic search"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """Semantic search using pgvector chunk embeddings."""
    from app.core.config import get_settings
    from app.services.llm_service import LLMService
    from app.services.search_service import SearchService

    start_time = time.time()

    if not q or not q.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    query = q.strip()
    settings = get_settings()
    llm = LLMService(settings)
    service = SearchService(llm_service=llm)
    offset = (page - 1) * page_size
    results = await service.semantic_search(query, limit=offset + page_size)
    page_results = results[offset : offset + page_size]
    execution_time_ms = (time.time() - start_time) * 1000

    return SearchResponse(
        query=query,
        results=page_results,
        total=len(results),
        page=page,
        page_size=page_size,
        execution_time_ms=round(execution_time_ms, 2),
    )


@router.get("/hybrid")
async def search_hybrid(
    q: str = Query(..., min_length=1, description="Search query for hybrid RRF search"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """Hybrid search: RRF fusion of chunk vectors and wiki full-text."""
    from app.core.config import get_settings
    from app.services.llm_service import LLMService
    from app.services.search_service import SearchService

    start_time = time.time()

    if not q or not q.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    query = q.strip()
    settings = get_settings()
    llm = LLMService(settings)
    service = SearchService(llm_service=llm)
    offset = (page - 1) * page_size
    results = await service.hybrid_search(query, limit=offset + page_size)
    page_results = results[offset : offset + page_size]
    execution_time_ms = (time.time() - start_time) * 1000

    return SearchResponse(
        query=query,
        results=page_results,
        total=len(results),
        page=page,
        page_size=page_size,
        execution_time_ms=round(execution_time_ms, 2),
    )


@router.get("/suggest")
async def search_suggest(
    q: str = Query(..., min_length=1, max_length=100),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """Autocomplete suggestions.

    Returns matching wiki page titles, entity names, and source titles
    that start with or contain the partial query string.
    """
    if not q or not q.strip():
        return {"query": "", "suggestions": []}

    query = q.strip()
    pattern = f"%{query}%"
    suggestions = []

    # Wiki page title suggestions
    wiki_result = await db.execute(
        select(WikiPage.title, WikiPage.slug)
        .where(WikiPage.title.ilike(pattern))
        .order_by(WikiPage.title)
        .limit(limit)
    )
    for row in wiki_result.all():
        title, slug = row
        suggestions.append({
            "text": title,
            "type": "wiki_page",
            "slug": slug,
        })

    # Entity name suggestions
    entity_result = await db.execute(
        select(Entity.name, Entity.entity_type)
        .where(Entity.name.ilike(pattern))
        .order_by(Entity.name)
        .limit(limit)
    )
    for row in entity_result.all():
        name, entity_type = row
        suggestions.append({
            "text": name,
            "type": "entity",
            "entity_type": entity_type,
        })

    # Source title suggestions
    source_result = await db.execute(
        select(Source.title, Source.file_type)
        .where(Source.title.ilike(pattern))
        .order_by(Source.title)
        .limit(limit)
    )
    for row in source_result.all():
        title, file_type = row
        suggestions.append({
            "text": title,
            "type": "source",
            "file_type": file_type,
        })

    # Deduplicate by text
    seen = set()
    unique_suggestions = []
    for s in suggestions:
        if s["text"].lower() not in seen:
            seen.add(s["text"].lower())
            unique_suggestions.append(s)

    # Sort by relevance (exact prefix match first)
    unique_suggestions.sort(
        key=lambda s: (0 if s["text"].lower().startswith(query.lower()) else 1, s["text"].lower())
    )

    return {
        "query": query,
        "suggestions": unique_suggestions[:limit],
    }
