"""Wiki page generation must be idempotent: regenerating a source replaces, not appends."""

import asyncio

from sqlalchemy import select

from app.core.database import async_session_maker
from app.models.entity import Entity
from app.models.wiki import WikiLink, WikiPage
from app.services.wiki_service import WikiService

run = asyncio.run


class TestWikiIdempotent:
    def test_delete_pages_for_source_removes_pages_links_and_clears_entity(
        self, client, create_source, create_wiki_page, create_entity, create_wiki_link
    ):
        source = create_source()
        other = create_source(
            title="Other", filename="o.txt", file_path="sources/2026/06/o.txt"
        )
        p1 = create_wiki_page(title="Page A", slug="page-a", source_id=source.id, page_type="concept")
        p2 = create_wiki_page(title="Page B", slug="page-b", source_id=source.id, page_type="concept")
        create_wiki_page(title="Keep", slug="keep", source_id=other.id, page_type="concept")
        ent = create_entity(name="E", wiki_page_id=p1.id)
        create_wiki_link(from_page_id=p1.id, to_page_id=p2.id, link_type="related")

        svc = WikiService(storage_service=None)
        removed = run(svc.delete_pages_for_source(source.id))
        assert removed == 2

        async def _check():
            async with async_session_maker() as s:
                pages = (
                    await s.execute(select(WikiPage.id).where(WikiPage.source_id == source.id))
                ).scalars().all()
                kept = (
                    await s.execute(select(WikiPage.id).where(WikiPage.source_id == other.id))
                ).scalars().all()
                links = (await s.execute(select(WikiLink.id))).scalars().all()
                e = (
                    await s.execute(select(Entity.wiki_page_id).where(Entity.id == ent.id))
                ).scalar()
                return pages, kept, links, e

        pages, kept, links, entity_page_id = run(_check())
        assert pages == []
        assert len(kept) == 1
        assert links == []
        assert entity_page_id is None

    def test_delete_pages_for_source_no_pages_is_noop(self, client, create_source):
        source = create_source()
        svc = WikiService(storage_service=None)
        assert run(svc.delete_pages_for_source(source.id)) == 0
