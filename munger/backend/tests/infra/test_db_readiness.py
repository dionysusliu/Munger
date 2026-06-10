"""Data-infra readiness: the suite must fail loudly if Postgres/pgvector/migrations aren't ready."""

from sqlalchemy import text

from app.core.config import get_settings
from app.core.database import Base, async_session_maker, engine
from tests.conftest import run_async

# Mirror of app/models/*.py __tablename__ — update when migrations add/rename tables
EXPECTED_TABLES = {
    "sources", "chunks", "chunk_extractions", "entities", "entity_mentions",
    "entity_relationships", "wiki_pages", "wiki_links", "ingest_jobs",
    "ingest_events", "configs", "ingestion_logs", "munger_analyses",
    "entity_edges", "communities",
}


def test_database_connection_works():
    async def _inner():
        async with async_session_maker() as session:
            return (await session.execute(text("SELECT 1"))).scalar()
    assert run_async(_inner()) == 1


def test_pgvector_extension_installed():
    async def _inner():
        async with async_session_maker() as session:
            return (await session.execute(
                text("SELECT count(*) FROM pg_extension WHERE extname = 'vector'")
            )).scalar()
    assert run_async(_inner()) == 1, "pgvector extension missing — run scripts/bootstrap_test_postgres.py"


def test_expected_tables_exist():
    async def _inner():
        async with engine.begin() as conn:
            rows = (await conn.execute(text(
                "SELECT table_name FROM information_schema.tables WHERE table_schema='public'"
            ))).scalars().all()
        return set(rows)
    present = run_async(_inner())
    missing = EXPECTED_TABLES - present
    assert not missing, f"missing tables (migrations not at head?): {missing}"


def test_embedding_dimension_matches_settings():
    settings = get_settings()
    # 768 is the current default; this asserts the DB schema matches the configured dimension.

    async def _inner():
        async with async_session_maker() as session:
            return (await session.execute(text(
                "SELECT a.atttypmod FROM pg_attribute a "
                "JOIN pg_class c ON c.oid = a.attrelid "
                "JOIN pg_namespace n ON n.oid = c.relnamespace "
                "WHERE c.relname='chunks' AND c.relkind='r' "
                "AND n.nspname='public' AND a.attname='embedding'"
            ))).scalar()
    dim = run_async(_inner())
    assert dim is not None, "chunks.embedding column not found — migrations may not be at head"
    assert dim == settings.embedding_dimensions, f"chunks.embedding dim {dim} != {settings.embedding_dimensions}"
