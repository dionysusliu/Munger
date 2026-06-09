"""Checkpointer provider with Postgres pool or in-memory fallback."""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from app.core.config import Settings

logger = logging.getLogger(__name__)

_checkpointer = None
_checkpointer_pool = None
_checkpointer_lock = asyncio.Lock()


async def get_async_checkpointer(settings: Settings):
    """Return a process-wide async checkpointer backed by a connection pool."""
    global _checkpointer, _checkpointer_pool

    if _checkpointer is not None:
        return _checkpointer

    async with _checkpointer_lock:
        if _checkpointer is not None:
            return _checkpointer

        url = (settings.checkpointer_url or "").strip()
        if url:
            try:
                from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
                from psycopg_pool import AsyncConnectionPool
            except ImportError as exc:
                raise ImportError(
                    "langgraph-checkpoint-postgres and psycopg-pool are required when MUNGER_CHECKPOINTER_URL is set"
                ) from exc

            # Setup must use an autocommit connection: migrations include CREATE INDEX CONCURRENTLY.
            async with AsyncPostgresSaver.from_conn_string(url) as setup_saver:
                await setup_saver.setup()

            pool = AsyncConnectionPool(conninfo=url, min_size=1, max_size=10, open=False)
            await pool.open()
            saver = AsyncPostgresSaver(pool)
            _checkpointer_pool = pool
            _checkpointer = saver
            logger.info("Checkpointer: using pooled AsyncPostgresSaver")
            return _checkpointer

        from langgraph.checkpoint.memory import InMemorySaver

        _checkpointer = InMemorySaver()
        logger.info("Checkpointer: using InMemorySaver (MUNGER_CHECKPOINTER_URL unset)")
        return _checkpointer


@asynccontextmanager
async def checkpointer_context(settings: Settings) -> AsyncIterator:
    """Yield a fresh checkpointer for tests (not cached)."""
    url = (settings.checkpointer_url or "").strip()
    if url:
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

        async with AsyncPostgresSaver.from_conn_string(url) as saver:
            await saver.setup()
            logger.info("Checkpointer: using AsyncPostgresSaver (context)")
            yield saver
        return

    from langgraph.checkpoint.memory import InMemorySaver

    logger.info("Checkpointer: using InMemorySaver (context)")
    yield InMemorySaver()


async def reset_checkpointer() -> None:
    """Reset the cached checkpointer (tests)."""
    global _checkpointer, _checkpointer_pool
    if _checkpointer_pool is not None:
        try:
            await _checkpointer_pool.close()
        except Exception:
            logger.warning("Error during checkpointer pool cleanup", exc_info=True)
        _checkpointer_pool = None
    _checkpointer = None
