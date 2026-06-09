"""Pydantic schemas for Source API."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class SourceBase(BaseModel):
    title: str = "Untitled"
    filename: str
    file_type: str  # pdf, txt, md, html, url
    source_url: Optional[str] = None


class SourceCreate(SourceBase):
    content_hash: str
    file_size: int = 0
    file_path: str


class SourceResponse(BaseModel):
    id: int
    title: str
    filename: str
    file_path: str
    file_type: str
    content_hash: str
    file_size: int
    content_summary: Optional[str] = None
    source_url: Optional[str] = None
    status: str
    error_message: Optional[str] = None
    metadata_json: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SourceList(BaseModel):
    items: list[SourceResponse]
    total: int
    page: int
    page_size: int
