"""Derived weighted undirected adjacency between (canonical) entities."""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import CheckConstraint, DateTime, Double, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class EntityEdge(Base):
    __tablename__ = "entity_edges"
    __table_args__ = (
        UniqueConstraint("src_entity_id", "tgt_entity_id", name="uq_entity_edges_pair"),
        CheckConstraint("src_entity_id < tgt_entity_id", name="ck_entity_edges_ordered"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    src_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    tgt_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    weight: Mapped[float] = mapped_column(Double, default=0.0)
    evidence_count: Mapped[int] = mapped_column(Integer, default=0)
    top_rel_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
