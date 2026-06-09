"""Ingestion log model - chronological record of system activities."""
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, DateTime, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class IngestionLog(Base):
    """Chronological log of ingestion, query, and lint operations."""
    __tablename__ = "ingestion_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("sources.id"), nullable=True
    )
    log_type: Mapped[str] = mapped_column(String(50))
    # ingest, query, lint, analysis, wiki_update, entity_extract
    action: Mapped[str] = mapped_column(String(200))
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
