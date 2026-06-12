import asyncio
import os
import shutil
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlparse

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

TEST_ROOT = Path(tempfile.mkdtemp(prefix="munger-backend-tests-"))
DATA_DIR = TEST_ROOT / "data"
BACKEND_ROOT = Path(__file__).resolve().parents[1]

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

DEFAULT_TEST_DATABASE_URL = (
    "postgresql+psycopg://munger_app:Munger.App.2026@localhost:5432/munger_test"
)
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", DEFAULT_TEST_DATABASE_URL)

_parsed = urlparse(TEST_DATABASE_URL.replace("postgresql+psycopg://", "postgresql://"))
_db_name = (_parsed.path or "").lstrip("/")
if _db_name == "munger":
    raise RuntimeError(
        "Refusing to run tests against production database 'munger'. "
        "Set TEST_DATABASE_URL to a dedicated test database (e.g. munger_test)."
    )

os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["DATA_DIR"] = str(DATA_DIR)
os.environ["DEBUG"] = "false"
os.environ["LLM_DEFAULT_PROVIDER"] = "ollama"
os.environ["OLLAMA_BASE_URL"] = "http://127.0.0.1:9"

from app.main import app  # noqa: E402
from app.core.database import Base, async_session_maker, engine  # noqa: E402
from app.models.entity import Entity, EntityMention  # noqa: E402
from app.models.log import IngestionLog  # noqa: E402
from app.models.source import Source  # noqa: E402
from app.models.wiki import WikiLink, WikiPage  # noqa: E402


def run_async(coro):
    return asyncio.run(coro)


def _reset_data_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    for subdir in ("sources", "wiki", "schema"):
        path = DATA_DIR / subdir
        if path.exists():
            shutil.rmtree(path)
        path.mkdir(parents=True, exist_ok=True)


async def _truncate_all_tables() -> None:
    table_names = [table.name for table in reversed(Base.metadata.sorted_tables)]
    if not table_names:
        return
    quoted = ", ".join(f'"{name}"' for name in table_names)
    async with engine.begin() as conn:
        await conn.execute(text(f"TRUNCATE {quoted} RESTART IDENTITY CASCADE"))


from app.db.migrate import run_migrations as _REAL_RUN_MIGRATIONS  # noqa: E402
# captured at import time: _tolerant_migrations may later be patched IN PLACE of
# app.db.migrate.run_migrations (client fixture) — calling through the module
# attribute would then recurse into itself.


def _tolerant_migrations():
    """Run alembic upgrade, tolerating a shared dev test-DB stamped AHEAD of this
    branch by a parallel worktree (e.g. a data-only migration). Alembic raises
    "Can't locate revision" in that case; the schema is a superset of what this
    branch needs, so proceed. Anything else is a real failure."""
    try:
        _REAL_RUN_MIGRATIONS()
    except Exception as exc:  # pragma: no cover - depends on shared-DB state
        if "Can't locate revision" not in str(exc):
            raise
        import logging
        logging.getLogger(__name__).warning(
            "test DB stamped ahead of this branch (%s); skipping upgrade", exc)


@pytest.fixture(scope="session", autouse=True)
def _run_migrations_once():
    _tolerant_migrations()
    # Kill DBOS zombies from a previous interrupted run: launch_dbos() RECOVERS any
    # non-terminal workflow from the dbos schema (which per-test truncation never
    # touches) and replays the ingest pipeline for sources that no longer exist —
    # the replay then throws FK violations / "No content_text" inside whatever
    # test happens to be running (observed as a cross-run flake since 2026-06-10).
    run_async(_purge_dbos_zombies())
    yield


async def _purge_dbos_zombies() -> None:
    from sqlalchemy import text as _text

    async with engine.begin() as conn:
        present = await conn.execute(_text(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema='dbos' AND table_name='workflow_status'"))
        if present.first() is None:
            return
        await conn.execute(_text(
            "DELETE FROM dbos.workflow_status WHERE status NOT IN ('SUCCESS', 'ERROR')"))


@pytest.fixture(scope="session")
def client():
    _reset_data_dirs()
    run_async(_truncate_all_tables())
    from unittest.mock import patch as _patch

    with _patch("app.db.migrate.run_migrations", new=_tolerant_migrations), TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def reset_state():
    _reset_data_dirs()
    run_async(_truncate_all_tables())
    yield


@pytest.fixture
def create_source():
    def _create_source(
        *,
        title="Sample Source",
        filename="sample.txt",
        file_path="sources/2026/06/sample.txt",
        file_type="txt",
        status="completed",
        content_text="Sample source content",
        content_summary=None,
        source_url=None,
    ):
        async def _inner():
            async with async_session_maker() as session:
                source = Source(
                    title=title,
                    filename=filename,
                    file_path=file_path,
                    file_type=file_type,
                    content_hash=f"hash-{title.lower().replace(' ', '-')}",
                    file_size=len(content_text.encode("utf-8")),
                    content_text=content_text,
                    content_summary=content_summary,
                    source_url=source_url,
                    status=status,
                )
                session.add(source)
                await session.commit()
                await session.refresh(source)
                return source

        return run_async(_inner())

    return _create_source


@pytest.fixture
def create_wiki_page():
    def _create_wiki_page(
        *,
        title="Sample Page",
        slug="sample-page",
        content="Sample page content",
        page_type="summary",
        source_id=None,
        parent_id=None,
    ):
        async def _inner():
            async with async_session_maker() as session:
                page = WikiPage(
                    title=title,
                    slug=slug,
                    content=content,
                    page_type=page_type,
                    source_id=source_id,
                    parent_id=parent_id,
                    word_count=len(content.split()),
                )
                session.add(page)
                await session.commit()
                await session.refresh(page)
                return page

        return run_async(_inner())

    return _create_wiki_page


@pytest.fixture
def create_entity():
    def _create_entity(
        *,
        name="Sample Entity",
        entity_type="concept",
        description="Entity description",
        wiki_page_id=None,
        mention_count=1,
    ):
        async def _inner():
            async with async_session_maker() as session:
                entity = Entity(
                    name=name,
                    entity_type=entity_type,
                    description=description,
                    wiki_page_id=wiki_page_id,
                    mention_count=mention_count,
                )
                session.add(entity)
                await session.commit()
                await session.refresh(entity)
                return entity

        return run_async(_inner())

    return _create_entity


@pytest.fixture
def create_entity_mention():
    def _create_entity_mention(*, entity_id, source_id=None, wiki_page_id=None, context="mention context"):
        async def _inner():
            async with async_session_maker() as session:
                mention = EntityMention(
                    entity_id=entity_id,
                    source_id=source_id,
                    wiki_page_id=wiki_page_id,
                    context=context,
                )
                session.add(mention)
                await session.commit()
                await session.refresh(mention)
                return mention

        return run_async(_inner())

    return _create_entity_mention


@pytest.fixture
def create_wiki_link():
    def _create_wiki_link(*, from_page_id, to_page_id, link_type="reference", context="linked"):
        async def _inner():
            async with async_session_maker() as session:
                link = WikiLink(
                    from_page_id=from_page_id,
                    to_page_id=to_page_id,
                    link_type=link_type,
                    context=context,
                )
                session.add(link)
                await session.commit()
                await session.refresh(link)
                return link

        return run_async(_inner())

    return _create_wiki_link


@pytest.fixture
def list_logs():
    def _list_logs():
        async def _inner():
            async with async_session_maker() as session:
                return list((await session.execute(IngestionLog.__table__.select())).all())

        return run_async(_inner())

    return _list_logs
