"""Chunk model — token-split document segments with optional embeddings."""

from datetime import datetime, timezone
from typing import Any, Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Chunk(Base):
    __tablename__ = "chunks"
    __table_args__ = (UniqueConstraint("source_id", "chunk_index", name="uq_chunks_source_index"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id", ondelete="CASCADE"), index=True)
    chunk_index: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    contextual_prefix: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    token_count: Mapped[int] = mapped_column(Integer)
    doc_char_start: Mapped[int] = mapped_column(Integer)
    doc_char_end: Mapped[int] = mapped_column(Integer)
    embedding: Mapped[Optional[Any]] = mapped_column(Vector(768), nullable=True)
    embedding_model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    map_status: Mapped[str] = mapped_column(String(20), default="pending")
    map_attempts: Mapped[int] = mapped_column(Integer, default=0)
    map_last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    mapped_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    map_started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    extractions: Mapped[list["ChunkExtraction"]] = relationship(
        "ChunkExtraction", back_populates="chunk", lazy="selectin"
    )
