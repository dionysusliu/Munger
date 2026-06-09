"""Shared DB helpers for ingest runtime nodes."""

import logging

from sqlalchemy import select, update

from app.core.database import async_session_maker
from app.models.log import IngestionLog
from app.models.source import Source

logger = logging.getLogger(__name__)


async def update_source_status(source_id: int, status: str) -> None:
    async with async_session_maker() as session:
        await session.execute(
            update(Source).where(Source.id == source_id).values(status=status)
        )
        await session.commit()
    logger.debug("Source %s status -> %s", source_id, status)


async def fail_source(source_id: int, message: str) -> None:
    async with async_session_maker() as session:
        await session.execute(
            update(Source)
            .where(Source.id == source_id)
            .values(status="failed", error_message=message)
        )
        await session.commit()
    logger.error("Source %s failed: %s", source_id, message)
    await log_ingestion(source_id, f"Ingestion failed: {message}")


async def log_ingestion(source_id: int, message: str) -> None:
    action = message if len(message) <= 200 else f"{message[:197]}..."
    async with async_session_maker() as session:
        session.add(
            IngestionLog(
                source_id=source_id,
                log_type="ingest",
                action=action,
                details=message if action != message else None,
            )
        )
        await session.commit()


async def get_source(source_id: int) -> Source | None:
    async with async_session_maker() as session:
        result = await session.execute(select(Source).where(Source.id == source_id))
        return result.scalar_one_or_none()
