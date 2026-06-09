"""Ingest timeline event model."""

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class IngestEvent(Base):
    """Chronological event emitted during an ingest agent run."""

    __tablename__ = "ingest_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"), index=True)
    job_id: Mapped[Optional[int]] = mapped_column(ForeignKey("ingest_jobs.id"), nullable=True, index=True)
    event_type: Mapped[str] = mapped_column(String(50), index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON().with_variant(JSONB, "postgresql"), default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)
