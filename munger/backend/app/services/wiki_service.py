"""Wiki service for page CRUD, cross-referencing, and index management."""

import logging
import re
from datetime import datetime

from sqlalchemy import select, func, and_, or_, desc, case
from sqlalchemy.orm import selectinload

from app.core.database import async_session_maker
from app.models.wiki import WikiPage, WikiLink
from app.models.log import IngestionLog
from app.schemas.wiki import WikiPageCreate, WikiPageResponse, WikiPageList, WikiLinkResponse

logger = logging.getLogger(__name__)


class WikiService:
    """Manages wiki page CRUD and cross-referencing."""

    def __init__(self, storage_service=None):
        self.storage_service = storage_service

    # ------------------------------------------------------------------
    # Page CRUD
    # ------------------------------------------------------------------

    async def create_page(self, data: WikiPageCreate) -> WikiPage:
        """Create a new wiki page."""
        async with async_session_maker() as session:
            # Generate slug from title if not provided
            slug = data.slug or self.generate_slug(data.title)

            # Check for duplicate slug
            existing = await session.execute(
                select(WikiPage).where(WikiPage.slug == slug)
            )
            if existing.scalar_one_or_none():
                # Append counter to make unique
                slug = await self._make_unique_slug(session, slug)

            word_count = len(data.content.split()) if data.content else 0

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
            session.add(page)
            await session.commit()
            await session.refresh(page)

            # Save to filesystem if storage service available
            if self.storage_service:
                try:
                    await self.storage_service.save_wiki_page(
                        slug, data.content, data.page_type
                    )
                except Exception as e:
                    logger.warning(f"Failed to save wiki page to filesystem: {e}")

            logger.info(f"Created wiki page: {page.title} (id={page.id}, slug={page.slug})")
            return page

    async def get_page(self, page_id: int) -> WikiPage | None:
        """Get a wiki page by ID with links."""
        async with async_session_maker() as session:
            result = await session.execute(
                select(WikiPage)
                .where(WikiPage.id == page_id)
                .options(
                    selectinload(WikiPage.outgoing_links),
                    selectinload(WikiPage.incoming_links),
                )
            )
            return result.scalar_one_or_none()

    async def get_page_by_slug(self, slug: str) -> WikiPage | None:
        """Get a wiki page by its slug."""
        async with async_session_maker() as session:
            result = await session.execute(
                select(WikiPage)
                .where(WikiPage.slug == slug)
                .options(
                    selectinload(WikiPage.outgoing_links),
                    selectinload(WikiPage.incoming_links),
                )
            )
            return result.scalar_one_or_none()

    async def update_page(self, page_id: int, content: str) -> WikiPage | None:
        """Update a wiki page's content."""
        async with async_session_maker() as session:
            result = await session.execute(
                select(WikiPage).where(WikiPage.id == page_id)
            )
            page = result.scalar_one_or_none()

            if not page:
                return None

            page.content = content
            page.word_count = len(content.split()) if content else 0
            page.updated_at = datetime.utcnow()

            await session.commit()
            await session.refresh(page)

            # Update filesystem
            if self.storage_service:
                try:
                    await self.storage_service.save_wiki_page(
                        page.slug, content, page.page_type
                    )
                except Exception as e:
                    logger.warning(f"Failed to update wiki page on filesystem: {e}")

            logger.info(f"Updated wiki page: {page.title} (id={page_id})")
            return page

    async def delete_page(self, page_id: int) -> bool:
        """Delete a wiki page and its links."""
        async with async_session_maker() as session:
            result = await session.execute(
                select(WikiPage).where(WikiPage.id == page_id)
            )
            page = result.scalar_one_or_none()

            if not page:
                return False

            # Delete from filesystem
            if self.storage_service:
                try:
                    await self.storage_service.delete_wiki_page(
                        page.slug, page.page_type
                    )
                except Exception as e:
                    logger.warning(f"Failed to delete wiki page from filesystem: {e}")

            await session.delete(page)
            await session.commit()

            logger.info(f"Deleted wiki page: {page.title} (id={page_id})")
            return True

    async def list_pages(
        self,
        page_type: str | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> WikiPageList:
        """List wiki pages with optional filters."""
        async with async_session_maker() as session:
            query = select(WikiPage)
            count_query = select(func.count(WikiPage.id))

            filters = []
            title_filter = None
            if page_type:
                filters.append(WikiPage.page_type == page_type)
            if search:
                search_term = f"%{search}%"
                title_filter = WikiPage.title.ilike(search_term)
                # Match title OR content, but rank title matches first.
                filters.append(or_(title_filter, WikiPage.content.ilike(search_term)))

            if filters:
                query = query.where(and_(*filters))
                count_query = count_query.where(and_(*filters))

            if title_filter is not None:
                query = query.order_by(
                    case((title_filter, 0), else_=1), desc(WikiPage.updated_at)
                )
            else:
                query = query.order_by(desc(WikiPage.updated_at))
            query = query.offset((page - 1) * page_size).limit(page_size)

            result = await session.execute(query)
            items = result.scalars().all()

            count_result = await session.execute(count_query)
            total = count_result.scalar()

            return WikiPageList(
                items=[WikiPageResponse.model_validate(p) for p in items],
                total=total,
                page=page,
                page_size=page_size,
            )

    # ------------------------------------------------------------------
    # Wiki links
    # ------------------------------------------------------------------

    async def create_link(
        self,
        from_id: int,
        to_id: int,
        link_type: str = "reference",
        context: str | None = None,
    ) -> WikiLink:
        """Create a link between two wiki pages."""
        async with async_session_maker() as session:
            # Check for existing link
            existing = await session.execute(
                select(WikiLink).where(
                    and_(
                        WikiLink.from_page_id == from_id,
                        WikiLink.to_page_id == to_id,
                    )
                )
            )
            if existing.scalar_one_or_none():
                # Update existing link
                link = existing.scalar_one()
                link.link_type = link_type
                if context:
                    link.context = context
                await session.commit()
                await session.refresh(link)
                return link

            link = WikiLink(
                from_page_id=from_id,
                to_page_id=to_id,
                link_type=link_type,
                context=context,
            )
            session.add(link)
            await session.commit()
            await session.refresh(link)

            logger.debug(f"Created wiki link: {from_id} -> {to_id} ({link_type})")
            return link

    async def get_page_links(self, page_id: int) -> list[WikiLinkResponse]:
        """Get all links for a page (both inbound and outbound)."""
        async with async_session_maker() as session:
            # Get page titles for link display
            result = await session.execute(
                select(WikiLink)
                .where(
                    or_(
                        WikiLink.from_page_id == page_id,
                        WikiLink.to_page_id == page_id,
                    )
                )
                .options(
                    selectinload(WikiLink.from_page),
                    selectinload(WikiLink.to_page),
                )
            )
            links = result.scalars().all()

            return [
                WikiLinkResponse(
                    id=link.id,
                    from_page_id=link.from_page_id,
                    to_page_id=link.to_page_id,
                    link_type=link.link_type,
                    context=link.context,
                    from_page_title=link.from_page.title if link.from_page else None,
                    to_page_title=link.to_page.title if link.to_page else None,
                )
                for link in links
            ]

    async def get_related_pages(self, page_id: int) -> list[WikiPage]:
        """Get pages related through wiki links."""
        async with async_session_maker() as session:
            # Get linked page IDs
            outbound = select(WikiLink.to_page_id).where(
                WikiLink.from_page_id == page_id
            )
            inbound = select(WikiLink.from_page_id).where(
                WikiLink.to_page_id == page_id
            )

            result = await session.execute(
                select(WikiPage)
                .where(
                    or_(
                        WikiPage.id.in_(outbound),
                        WikiPage.id.in_(inbound),
                    )
                )
                .distinct()
                .limit(20)
            )
            return list(result.scalars().all())

    # ------------------------------------------------------------------
    # Wiki link resolution
    # ------------------------------------------------------------------

    async def resolve_wiki_links(self, content: str) -> str:
        """Convert [[Page Name]] syntax to wiki links.

        Looks up existing pages and replaces [[Name]] with markdown links.
        """
        if "[[" not in content:
            return content

        # Find all [[...]] references
        pattern = re.compile(r"\[\[([^\]]+)\]\]")

        async with async_session_maker() as session:
            def replace_link(match):
                page_name = match.group(1).strip()
                # Look up page by title
                result = session.sync_session.execute(
                    select(WikiPage).where(
                        func.lower(WikiPage.title) == page_name.lower()
                    )
                )
                page = result.scalar_one_or_none()

                if page:
                    return f"[{page_name}](/wiki/{page.slug})"
                else:
                    # Unresolved link
                    return f"[{page_name}](?unresolved)"

            # Process replacements
            resolved = pattern.sub(replace_link, content)
            return resolved

    # ------------------------------------------------------------------
    # Slug generation
    # ------------------------------------------------------------------

    def generate_slug(self, title: str) -> str:
        """Generate a URL-friendly slug from a title."""
        # Convert to lowercase
        slug = title.lower()
        # Replace special characters
        slug = re.sub(r"[^a-z0-9\s-]", "", slug)
        # Replace spaces and underscores with hyphens
        slug = re.sub(r"[\s_]+", "-", slug)
        # Collapse multiple hyphens
        slug = re.sub(r"-+", "-", slug)
        # Trim hyphens from ends
        slug = slug.strip("-")
        # Limit length
        if len(slug) > 100:
            slug = slug[:100].rsplit("-", 1)[0]
        return slug or "untitled"

    async def _make_unique_slug(self, session, base_slug: str) -> str:
        """Append a counter to make a slug unique."""
        counter = 1
        slug = base_slug
        while True:
            result = await session.execute(select(WikiPage).where(WikiPage.slug == slug))
            if not result.scalar_one_or_none():
                return slug
            counter += 1
            slug = f"{base_slug}-{counter}"

    # ------------------------------------------------------------------
    # Index management
    # ------------------------------------------------------------------

    async def update_index(self) -> None:
        """Regenerate the wiki index page."""
        async with async_session_maker() as session:
            # Get all pages grouped by type
            result = await session.execute(
                select(WikiPage).order_by(WikiPage.title)
            )
            pages = result.scalars().all()

            # Group by type
            by_type: dict[str, list[WikiPage]] = {}
            for page in pages:
                by_type.setdefault(page.page_type, []).append(page)

            # Build index content
            lines = [
                "# Munger Knowledge Base Index",
                "",
                f"*Last updated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC*",
                "",
                f"**Total pages: {len(pages)}**",
                "",
                "---",
                "",
            ]

            # Summary pages first
            for page_type in ["summary", "overview", "index", "entity", "concept", "model",
                               "mechanism", "incentive", "psychology", "analysis"]:
                if page_type not in by_type:
                    continue
                type_pages = by_type[page_type]
                lines.append(f"## {page_type.replace('_', ' ').title()} ({len(type_pages)})")
                lines.append("")
                for page in sorted(type_pages, key=lambda p: p.title):
                    lines.append(f"- [[{page.title}]] — {page.slug}")
                lines.append("")

            # Any remaining types
            for page_type, type_pages in sorted(by_type.items()):
                if page_type in ["summary", "overview", "index", "entity", "concept", "model",
                                  "mechanism", "incentive", "psychology", "analysis"]:
                    continue
                lines.append(f"## {page_type.replace('_', ' ').title()} ({len(type_pages)})")
                lines.append("")
                for page in sorted(type_pages, key=lambda p: p.title):
                    lines.append(f"- [[{page.title}]] — {page.slug}")
                lines.append("")

            index_content = "\n".join(lines)

            # Save to filesystem
            if self.storage_service:
                await self.storage_service.write_index(index_content)

            # Update or create index page in DB
            index_page = await session.execute(
                select(WikiPage).where(WikiPage.page_type == "index")
            )
            existing = index_page.scalar_one_or_none()

            if existing:
                existing.content = index_content
                existing.word_count = len(index_content.split())
                existing.updated_at = datetime.utcnow()
            else:
                new_index = WikiPage(
                    title="Knowledge Base Index",
                    slug="index",
                    content=index_content,
                    page_type="index",
                    word_count=len(index_content.split()),
                )
                session.add(new_index)

            await session.commit()
            logger.info("Updated wiki index")

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------

    async def append_log(self, action: str, details: str | None = None) -> None:
        """Append an entry to the ingestion log."""
        async with async_session_maker() as session:
            log_entry = IngestionLog(
                log_type="wiki_update",
                action=action,
                details=details,
            )
            session.add(log_entry)
            await session.commit()

        # Also append to filesystem log
        if self.storage_service:
            try:
                await self.storage_service.append_to_log(
                    f"**{action}**\n\n{details or ''}"
                )
            except Exception as e:
                logger.warning(f"Failed to append to filesystem log: {e}")

        logger.debug(f"Log entry: {action}")
