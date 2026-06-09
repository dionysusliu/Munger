"""Pydantic schemas for Search API."""
from typing import Optional
from pydantic import BaseModel


class SearchResult(BaseModel):
    id: int
    title: str
    content: str
    result_type: str  # wiki_page, source, entity, chunk
    score: float
    slug: Optional[str] = None
    entity_type: Optional[str] = None
    page_type: Optional[str] = None
    source_id: Optional[int] = None
    chunk_id: Optional[int] = None
    char_start: Optional[int] = None
    char_end: Optional[int] = None
    excerpt: Optional[str] = None


class SearchRequest(BaseModel):
    query: str
    result_type: Optional[str] = None  # wiki_page, source, entity, all
    page: int = 1
    page_size: int = 20


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResult]
    total: int
    page: int
    page_size: int
    execution_time_ms: float
