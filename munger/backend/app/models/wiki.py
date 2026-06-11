"""Wiki page and link models - the knowledge graph core."""
from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Text, DateTime, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class WikiPage(Base):
    """A wiki page - LLM-generated knowledge entry."""
    __tablename__ = "wiki_pages"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(500))
    slug: Mapped[str] = mapped_column(String(500), unique=True, index=True)
    content: Mapped[str] = mapped_column(Text, default="")
    page_type: Mapped[str] = mapped_column(String(50), default="summary")
    # 7-type ontology (see app/prompts/ontology.py): person, organization, work,
    # concept, mental_model, mechanism, event — plus summary/index for non-entity pages
    source_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("sources.id"), nullable=True
    )
    parent_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("wiki_pages.id"), nullable=True
    )
    metadata_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    word_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    source: Mapped[Optional["Source"]] = relationship(
        "Source", back_populates="wiki_pages"
    )
    outgoing_links: Mapped[List["WikiLink"]] = relationship(
        "WikiLink",
        foreign_keys="WikiLink.from_page_id",
        back_populates="from_page",
        lazy="selectin",
    )
    incoming_links: Mapped[List["WikiLink"]] = relationship(
        "WikiLink",
        foreign_keys="WikiLink.to_page_id",
        back_populates="to_page",
        lazy="selectin",
    )
    munger_analyses: Mapped[List["MungerAnalysis"]] = relationship(
        "MungerAnalysis", back_populates="wiki_page", lazy="selectin"
    )


class WikiLink(Base):
    """A link between two wiki pages - represents relationships in the knowledge graph."""
    __tablename__ = "wiki_links"

    id: Mapped[int] = mapped_column(primary_key=True)
    from_page_id: Mapped[int] = mapped_column(ForeignKey("wiki_pages.id"))
    to_page_id: Mapped[int] = mapped_column(ForeignKey("wiki_pages.id"))
    link_type: Mapped[str] = mapped_column(String(50), default="reference")
    # reference, contradicts, supports, relates, parent, child
    context: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    from_page: Mapped["WikiPage"] = relationship(
        "WikiPage", foreign_keys=[from_page_id], back_populates="outgoing_links"
    )
    to_page: Mapped["WikiPage"] = relationship(
        "WikiPage", foreign_keys=[to_page_id], back_populates="incoming_links"
    )
