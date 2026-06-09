"""Pydantic schemas for Config API."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class ConfigUpdate(BaseModel):
    value: str


class ConfigResponse(BaseModel):
    id: int
    key: str
    value: str
    description: Optional[str] = None
    updated_at: datetime

    class Config:
        from_attributes = True


class ModelInfo(BaseModel):
    id: str
    name: str
    provider: str
    description: Optional[str] = None
    available: bool
