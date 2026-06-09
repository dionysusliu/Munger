"""Extracted entity-to-entity relationships (LightRAG-style edges)."""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, Double, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class EntityRelationship(Base):
    __tablename__ = "entity_relationships"
    __table_args__ = (
        UniqueConstraint(
            "source_entity_id",
            "target_entity_id",
            "relationship_type",
            "source_id",
            name="uq_entity_relationships_quad",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    target_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    relationship_type: Mapped[str] = mapped_column(String(50))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Added by migration 004_cross_chunk_linking; nullable so pre-migration rows remain valid.
    confidence: Mapped[Optional[float]] = mapped_column(Double, nullable=True)
    method: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    source_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("sources.id", ondelete="CASCADE"), nullable=True
    )
    chunk_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("chunks.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
