"""Pydantic schemas for Munger Analysis API."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class MungerAnalysisBase(BaseModel):
    dimension: str
    dimension_number: int
    analysis_content: str
    confidence: float = 0.0
    key_insights: Optional[str] = None


class MungerAnalysisCreate(MungerAnalysisBase):
    source_id: Optional[int] = None
    wiki_page_id: Optional[int] = None


class MungerAnalysisResponse(BaseModel):
    id: int
    source_id: Optional[int] = None
    wiki_page_id: Optional[int] = None
    dimension: str
    dimension_number: int
    analysis_content: str
    confidence: float
    key_insights: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class MungerDimensionInfo(BaseModel):
    number: int
    key: str
    name: str
    name_en: str
    description: str
    questions: list[str]
