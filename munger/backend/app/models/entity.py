"""Entity and entity mention models - extracted named entities from sources."""
from datetime import datetime
from typing import Any, List, Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import Double, String, Text, DateTime, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Entity(Base):
    """An entity - person, concept, model, book, etc. extracted from sources."""
    __tablename__ = "entities"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), index=True)
    entity_type: Mapped[str] = mapped_column(String(50))
    # 7-type ontology (see app/prompts/ontology.py): person, organization, work,
    # concept, mental_model, mechanism, event
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    wiki_page_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("wiki_pages.id"), nullable=True
    )
    metadata_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    mention_count: Mapped[int] = mapped_column(Integer, default=1)
    embedding: Mapped[Optional[Any]] = mapped_column(Vector(768), nullable=True)
    salience: Mapped[float] = mapped_column(Double, default=0.0)
    canonical_entity_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("entities.id", ondelete="SET NULL"), nullable=True
    )
    community_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("communities.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    wiki_page: Mapped[Optional["WikiPage"]] = relationship("WikiPage", lazy="selectin")
    mentions: Mapped[List["EntityMention"]] = relationship(
        "EntityMention", back_populates="entity", lazy="selectin"
    )


class EntityMention(Base):
    """A mention of an entity in a source or wiki page."""
    __tablename__ = "entity_mentions"

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id"))
    source_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("sources.id"), nullable=True
    )
    wiki_page_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("wiki_pages.id"), nullable=True
    )
    chunk_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("chunks.id", ondelete="SET NULL"), nullable=True
    )
    char_start: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    char_end: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    context: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    mention_method: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, default="extract")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    entity: Mapped["Entity"] = relationship("Entity", back_populates="mentions")
