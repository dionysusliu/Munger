"""Database configuration and session management."""
from contextvars import ContextVar
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

from app.core.config import get_settings

settings = get_settings()


def normalize_async_database_url(url: str) -> str:
    """Convert a configured DATABASE_URL to an async SQLAlchemy URL."""
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


def normalize_sync_database_url(url: str) -> str:
    """Convert a configured DATABASE_URL to a sync SQLAlchemy/Alembic URL."""
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


DATABASE_URL = normalize_async_database_url(settings.database_url)
SYNC_DATABASE_URL = normalize_sync_database_url(settings.database_url)

Base = declarative_base()

engine = create_async_engine(
    DATABASE_URL,
    echo=settings.debug,
    future=True,
)

_default_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# The "current" sessionmaker is held in a ContextVar so an isolated execution
# context (e.g. the DBOS ingest step, which runs the pipeline in its own thread
# and event loop) can bind a loop-local engine without disturbing the worker
# loop's global engine. Normal callers transparently get the global maker.
_session_maker_var: ContextVar = ContextVar(
    "munger_session_maker", default=_default_session_maker
)


def async_session_maker() -> AsyncSession:
    """Return an AsyncSession from the context-current sessionmaker.

    Use exactly as before: ``async with async_session_maker() as session:``.
    Resolution happens at call time, so a context that overrides
    ``_session_maker_var`` transparently gets sessions from its own engine.
    """
    return _session_maker_var.get()()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting async database sessions."""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
