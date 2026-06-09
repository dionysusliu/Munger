"""Ingest job queue model."""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class IngestJob(Base):
    """Durable queue row for a single source ingest run."""

    __tablename__ = "ingest_jobs"
    __table_args__ = (
        Index(
            "uq_ingest_jobs_active_source",
            "source_id",
            unique=True,
            postgresql_where=text("status IN ('pending','claimed','running')"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"), index=True)
    skill_name: Mapped[str] = mapped_column(String(50), default="ingest")
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    thread_id: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    claimed_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    heartbeat_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )
