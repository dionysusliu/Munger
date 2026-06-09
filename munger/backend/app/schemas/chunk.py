"""Pydantic schemas for chunks and provenance."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ChunkResponse(BaseModel):
    id: int
    source_id: int
    chunk_index: int
    content: str
    contextual_prefix: Optional[str] = None
    token_count: int
    doc_char_start: int
    doc_char_end: int
    created_at: datetime

    class Config:
        from_attributes = True


class ProvenanceChainItem(BaseModel):
    source_id: int
    chunk_id: int
    char_start: int
    char_end: int
    excerpt: str
