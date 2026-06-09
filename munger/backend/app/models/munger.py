"""Munger analysis model - 12-dimension thinking framework results."""
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, DateTime, Integer, ForeignKey, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class MungerAnalysis(Base):
    """Munger 12-dimension analysis result for a source or wiki page."""
    __tablename__ = "munger_analyses"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("sources.id"), nullable=True
    )
    wiki_page_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("wiki_pages.id"), nullable=True
    )
    dimension: Mapped[str] = mapped_column(String(50))
    # source, claim, concept, model, mechanism, incentive,
    # psychology, dual_track, counterargument, checklist, case, decision
    dimension_number: Mapped[int] = mapped_column(Integer)
    analysis_content: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    key_insights: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    source: Mapped[Optional["Source"]] = relationship(
        "Source", back_populates="munger_analyses"
    )
    wiki_page: Mapped[Optional["WikiPage"]] = relationship(
        "WikiPage", back_populates="munger_analyses"
    )
