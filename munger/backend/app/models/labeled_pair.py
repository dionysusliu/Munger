"""Human-decided entity match/reject pairs (HITL input to resolution)."""

from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class LabeledPair(Base):
    __tablename__ = "labeled_pairs"
    __table_args__ = (
        CheckConstraint("entity_a_id < entity_b_id", name="ck_labeled_pairs_ordered"),
        UniqueConstraint("entity_a_id", "entity_b_id", name="uq_labeled_pairs_pair"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_a_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    entity_b_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    label: Mapped[str] = mapped_column(String(10))  # "match" | "reject"
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
