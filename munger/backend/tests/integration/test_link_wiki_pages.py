"""Characterization for the link_wiki_pages step (n_wiki second phase).

link_wiki_pages creates WikiLink(link_type="related") between two entity wiki
pages when one page's body mentions the other entity's name (regex match,
nodes_cognify.py ~300-326). The default scripted LLM returns bland bodies that
never cross-reference, so this drives the real graph with a fake LLM whose
generated page bodies DO mention the other entity names.
"""

from sqlalchemy import func, select

from app.core.config import Settings
from app.core.database import async_session_maker
from app.models.wiki import WikiLink, WikiPage
from app.runtime.context import RuntimeServices
from app.runtime.graphs.ingest import build_ingest_graph
from tests.conftest import run_async
from tests.fixtures.fake_llm import ScriptedLLMService
from tests.fixtures.ingest_fixtures import two_entity_scripts


class CrossRefLLM(ScriptedLLMService):
    """Like ScriptedLLMService, but every generated wiki page body mentions all
    known entity names, so link_wiki_pages can cross-link the pages."""

    def __init__(self, scripts, entity_names):
        super().__init__(scripts)
        self._entity_names = entity_names

    async def generate_wiki_page(self, title: str, content: str, page_type: str = "entity") -> str:
        related = ", ".join(self._entity_names)
        return f"# {title}\n\nRelated entities: {related}."


def test_link_wiki_pages_creates_related_links(create_source):
    source = create_source(
        status="pending",
        content_text="Charlie Munger champions Mental Models as a latticework for decisions.",
    )
    settings = Settings(
        ingest_orchestrator="graph",
        ingest_map_mode="service",
        ingest_max_gleanings=0,
        # Pin to 1 so both scripted entities (each with mention_count=1) get wiki pages;
        # this test verifies link_wiki_pages creates cross-links, not the singleton gate.
        ingest_wiki_min_mentions=1,
    )
    # script[0] is consumed by the contextual-prefix chat() call; script[1] is the
    # entity extraction dict (same ordering rationale as the E2E oracle).
    scripts = ["Munger document context."] + two_entity_scripts()
    llm = CrossRefLLM(scripts, entity_names=["Charlie Munger", "Mental Models"])
    services = RuntimeServices.from_settings(settings, llm=llm)
    graph = build_ingest_graph(services, checkpointer=None)

    run_async(
        graph.ainvoke(
            {"source_id": source.id, "job_id": None},
            config={"configurable": {"thread_id": f"linkwiki-{source.id}"}},
        )
    )

    async def _counts():
        async with async_session_maker() as session:
            entity_pages = (
                await session.execute(
                    select(func.count())
                    .select_from(WikiPage)
                    .where(WikiPage.source_id == source.id, WikiPage.page_type != "summary")
                )
            ).scalar()
            related = (
                await session.execute(
                    select(func.count())
                    .select_from(WikiLink)
                    .where(WikiLink.link_type == "related")
                )
            ).scalar()
            return entity_pages, related

    entity_pages, related = run_async(_counts())
    assert entity_pages >= 2, "expected one wiki page per scripted entity"
    assert related >= 1, "link_wiki_pages must create related links when page bodies cross-reference"
