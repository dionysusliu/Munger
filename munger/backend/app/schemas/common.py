"""Common Pydantic schemas."""
from typing import TypeVar, Generic, Optional
from pydantic import BaseModel

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int


class StatsResponse(BaseModel):
    total_sources: int
    total_wiki_pages: int
    total_entities: int
    total_links: int
    recent_sources: int  # last 7 days
    recent_wiki_pages: int
    sources_by_type: dict[str, int]
    wiki_pages_by_type: dict[str, int]
    entities_by_type: dict[str, int]
