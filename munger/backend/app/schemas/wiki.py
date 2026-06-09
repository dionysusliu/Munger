"""Pydantic schemas for Wiki API."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class WikiPageBase(BaseModel):
    title: str
    content: str = ""
    page_type: str = "summary"
    metadata_json: Optional[str] = None


class WikiPageCreate(WikiPageBase):
    slug: str
    source_id: Optional[int] = None
    parent_id: Optional[int] = None


class WikiPageResponse(BaseModel):
    id: int
    title: str
    slug: str
    content: str
    page_type: str
    source_id: Optional[int] = None
    parent_id: Optional[int] = None
    metadata_json: Optional[str] = None
    word_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WikiPageList(BaseModel):
    items: list[WikiPageResponse]
    total: int
    page: int
    page_size: int


class WikiLinkResponse(BaseModel):
    id: int
    from_page_id: int
    to_page_id: int
    link_type: str
    context: Optional[str] = None
    from_page_title: Optional[str] = None
    to_page_title: Optional[str] = None

    class Config:
        from_attributes = True
