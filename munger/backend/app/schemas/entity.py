"""Pydantic schemas for Entity API."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class EntityBase(BaseModel):
    name: str
    entity_type: str
    description: Optional[str] = None
    metadata_json: Optional[str] = None


class EntityCreate(EntityBase):
    wiki_page_id: Optional[int] = None


class EntityResponse(BaseModel):
    id: int
    name: str
    entity_type: str
    description: Optional[str] = None
    wiki_page_id: Optional[int] = None
    metadata_json: Optional[str] = None
    mention_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class EntityList(BaseModel):
    items: list[EntityResponse]
    total: int
    page: int
    page_size: int


class EntityMentionResponse(BaseModel):
    id: int
    entity_id: int
    source_id: Optional[int] = None
    wiki_page_id: Optional[int] = None
    chunk_id: Optional[int] = None
    char_start: Optional[int] = None
    char_end: Optional[int] = None
    context: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
