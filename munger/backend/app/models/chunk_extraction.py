"""Raw per-chunk entity/relationship extraction results."""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ChunkExtraction(Base):
    __tablename__ = "chunk_extractions"
    __table_args__ = (UniqueConstraint("chunk_id", "glean_round", name="uq_chunk_extractions_round"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    chunk_id: Mapped[int] = mapped_column(ForeignKey("chunks.id", ondelete="CASCADE"), index=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id", ondelete="CASCADE"), index=True)
    entities: Mapped[list[Any]] = mapped_column(JSON().with_variant(JSONB, "postgresql"), default=list)
    relationships: Mapped[list[Any]] = mapped_column(JSON().with_variant(JSONB, "postgresql"), default=list)
    glean_round: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    chunk: Mapped["Chunk"] = relationship("Chunk", back_populates="extractions")
