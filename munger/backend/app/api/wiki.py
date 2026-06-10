"""Wiki page API routes for Munger."""
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.wiki import WikiPage, WikiLink
from app.models.entity import Entity
from app.models.munger import MungerAnalysis
from app.schemas.wiki import (
    WikiPageCreate,
    WikiPageResponse,
    WikiPageList,
    WikiLinkResponse,
)
from app.utils.text_utils import generate_slug, count_words, extract_markdown_links

router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _get_page_or_404(db: AsyncSession, page_id: int) -> WikiPage:
    page = await db.get(WikiPage, page_id)
    if not page:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wiki page not found")
    return page


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("", response_model=WikiPageList)
async def list_wiki_pages(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=500),
    page_type: Optional[str] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """List wiki pages with pagination, optional type filter, and search."""
    query = select(WikiPage)
    count_query = select(func.count(WikiPage.id))

    if page_type:
        query = query.where(WikiPage.page_type == page_type)
        count_query = count_query.where(WikiPage.page_type == page_type)

    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            WikiPage.title.ilike(search_pattern) | WikiPage.content.ilike(search_pattern)
        )
        count_query = count_query.where(
            WikiPage.title.ilike(search_pattern) | WikiPage.content.ilike(search_pattern)
        )

    query = query.order_by(desc(WikiPage.updated_at))

    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    result = await db.execute(query)
    pages = result.scalars().all()

    total_result = await db.execute(count_query)
    total = total_result.scalar()

    return WikiPageList(
        items=list(pages),
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=WikiPageResponse, status_code=status.HTTP_201_CREATED)
async def create_wiki_page(
    data: WikiPageCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new wiki page manually.

    If no slug is provided, one is generated from the title.
    """
    slug = data.slug or generate_slug(data.title)

    # Check for duplicate slug
    existing = await db.execute(select(WikiPage).where(WikiPage.slug == slug))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Wiki page with slug '{slug}' already exists",
        )

    word_count = count_words(data.content)

    page = WikiPage(
        title=data.title,
        slug=slug,
        content=data.content,
        page_type=data.page_type,
        source_id=data.source_id,
        parent_id=data.parent_id,
        metadata_json=data.metadata_json,
        word_count=word_count,
    )
    db.add(page)
    await db.flush()
    await db.refresh(page)

    return page


@router.get("/{page_id}", response_model=WikiPageResponse)
async def get_wiki_page(
    page_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get a wiki page by ID."""
    return await _get_page_or_404(db, page_id)


@router.get("/slug/{slug}", response_model=WikiPageResponse)
async def get_wiki_page_by_slug(
    slug: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a wiki page by its slug."""
    result = await db.execute(select(WikiPage).where(WikiPage.slug == slug))
    page = result.scalar_one_or_none()
    if not page:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wiki page not found")
    return page


@router.put("/{page_id}", response_model=WikiPageResponse)
async def update_wiki_page(
    page_id: int,
    content: str,
    db: AsyncSession = Depends(get_db),
):
    """Update wiki page content (manual edit).

    Recomputes word count and updates the ``updated_at`` timestamp.
    """
    page = await _get_page_or_404(db, page_id)

    page.content = content
    page.word_count = count_words(content)
    page.updated_at = datetime.now(timezone.utc)

    await db.flush()
    await db.refresh(page)

    return page


@router.delete("/{page_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_wiki_page(
    page_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete a wiki page and all associated links."""
    page = await _get_page_or_404(db, page_id)

    # Delete associated links (both incoming and outgoing)
    from sqlalchemy import delete
    await db.execute(delete(WikiLink).where(WikiLink.from_page_id == page_id))
    await db.execute(delete(WikiLink).where(WikiLink.to_page_id == page_id))

    # Delete associated Munger analyses
    await db.execute(delete(MungerAnalysis).where(MungerAnalysis.wiki_page_id == page_id))

    await db.delete(page)

    return None


@router.get("/{page_id}/links")
async def get_wiki_links(
    page_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get all links for a wiki page (both inbound and outbound).

    Returns a combined list of WikiLink objects with page titles.
    """
    page = await _get_page_or_404(db, page_id)

    # Outgoing links
    outgoing_result = await db.execute(
        select(
            WikiLink,
            WikiPage.title.label("to_page_title"),
            WikiPage.slug.label("to_page_slug"),
        )
        .join(WikiPage, WikiLink.to_page_id == WikiPage.id)
        .where(WikiLink.from_page_id == page_id)
    )
    outgoing = []
    for row in outgoing_result.all():
        link, to_title, to_slug = row
        outgoing.append({
            "id": link.id,
            "from_page_id": link.from_page_id,
            "to_page_id": link.to_page_id,
            "link_type": link.link_type,
            "context": link.context,
            "from_page_title": page.title,
            "from_page_slug": page.slug,
            "to_page_title": to_title,
            "to_page_slug": to_slug,
            "direction": "outgoing",
        })

    # Incoming links
    incoming_result = await db.execute(
        select(
            WikiLink,
            WikiPage.title.label("from_page_title"),
            WikiPage.slug.label("from_page_slug"),
        )
        .join(WikiPage, WikiLink.from_page_id == WikiPage.id)
        .where(WikiLink.to_page_id == page_id)
    )
    incoming = []
    for row in incoming_result.all():
        link, from_title, from_slug = row
        incoming.append({
            "id": link.id,
            "from_page_id": link.from_page_id,
            "to_page_id": link.to_page_id,
            "link_type": link.link_type,
            "context": link.context,
            "from_page_title": from_title,
            "from_page_slug": from_slug,
            "to_page_title": page.title,
            "to_page_slug": page.slug,
            "direction": "incoming",
        })

    return {
        "page_id": page_id,
        "outgoing": outgoing,
        "incoming": incoming,
        "total": len(outgoing) + len(incoming),
    }


@router.get("/{page_id}/related")
async def get_related_pages(
    page_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get related wiki pages.

    Related pages are determined by:
    1. Pages linked from this page (outgoing)
    2. Pages linking to this page (incoming)
    3. Pages sharing the same source
    4. Pages of the same type
    """
    page = await _get_page_or_404(db, page_id)

    related_ids = set()

    # Outgoing links
    result = await db.execute(
        select(WikiLink.to_page_id).where(WikiLink.from_page_id == page_id)
    )
    for row in result.all():
        related_ids.add(row[0])

    # Incoming links
    result = await db.execute(
        select(WikiLink.from_page_id).where(WikiLink.to_page_id == page_id)
    )
    for row in result.all():
        related_ids.add(row[0])

    # Same source
    if page.source_id:
        result = await db.execute(
            select(WikiPage.id)
            .where(WikiPage.source_id == page.source_id)
            .where(WikiPage.id != page_id)
        )
        for row in result.all():
            related_ids.add(row[0])

    if not related_ids:
        return {"page_id": page_id, "related_pages": []}

    # Fetch related pages
    result = await db.execute(
        select(WikiPage)
        .where(WikiPage.id.in_(list(related_ids)))
        .order_by(desc(WikiPage.updated_at))
        .limit(20)
    )
    related_pages = result.scalars().all()

    return {
        "page_id": page_id,
        "related_pages": [
            {
                "id": p.id,
                "title": p.title,
                "slug": p.slug,
                "page_type": p.page_type,
                "word_count": p.word_count,
                "updated_at": p.updated_at,
            }
            for p in related_pages
        ],
    }
