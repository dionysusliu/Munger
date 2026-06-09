"""Source model - original materials ingested into Munger."""
from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Text, DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Source(Base):
    """Original source material - immutable once ingested."""
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(500), default="Untitled")
    filename: Mapped[str] = mapped_column(String(500))
    file_path: Mapped[str] = mapped_column(String(1000))  # relative to sources_dir
    file_type: Mapped[str] = mapped_column(String(50))  # pdf, txt, md, html, url
    content_hash: Mapped[str] = mapped_column(String(64))  # sha256
    chunked_content_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    file_size: Mapped[int] = mapped_column(Integer, default=0)
    content_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    content_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_url: Mapped[Optional[str]] = mapped_column(String(2000), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    # pending, extracting, summarizing, extracting_entities, creating_pages, analyzing, completed, failed
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    wiki_pages: Mapped[List["WikiPage"]] = relationship(
        "WikiPage", back_populates="source", lazy="selectin"
    )
    munger_analyses: Mapped[List["MungerAnalysis"]] = relationship(
        "MungerAnalysis", back_populates="source", lazy="selectin"
    )
