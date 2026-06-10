"""Regression: WikiService.create_link must UPDATE an existing (from,to) pair.

Previously the update branch called scalar_one_or_none() then scalar_one() on the
same (exhausted) Result, raising "This result object is closed" — so re-linking the
same page pair (e.g. re-ingesting a source) failed instead of updating.
"""

from sqlalchemy import func, select

from app.core.database import async_session_maker
from app.models.wiki import WikiLink
from tests.conftest import run_async
from tests.fixtures.ingest_fixtures import scripted_services


def test_create_link_twice_updates_existing_pair(create_wiki_page):
    a = create_wiki_page(title="Link A", slug="link-a")
    b = create_wiki_page(title="Link B", slug="link-b")
    wiki = scripted_services([]).wiki

    async def _inner():
        first = await wiki.create_link(a.id, b.id, link_type="reference", context="c1")
        # Second call on the SAME pair must update the existing row (this used to raise).
        second = await wiki.create_link(a.id, b.id, link_type="related", context="c2")
        async with async_session_maker() as session:
            count = (
                await session.execute(
                    select(func.count())
                    .select_from(WikiLink)
                    .where(WikiLink.from_page_id == a.id, WikiLink.to_page_id == b.id)
                )
            ).scalar()
        return first.id, second.id, second.link_type, second.context, count

    first_id, second_id, link_type, context, count = run_async(_inner())
    assert first_id == second_id, "second create_link must update the same row, not insert a new one"
    assert link_type == "related", "link_type must be updated on the second call"
    assert context == "c2", "context must be updated on the second call"
    assert count == 1, "no duplicate WikiLink row should be created"
