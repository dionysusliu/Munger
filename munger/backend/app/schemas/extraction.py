"""Pydantic schemas for structured entity extraction."""

from pydantic import BaseModel, Field


class ExtractedEntity(BaseModel):
    name: str = Field(description="Canonical entity name")
    type: str = Field(description="Entity type")
    description: str = Field(default="", description="Brief description from source text")
    char_start: int | None = Field(default=None, description="Document-global char start")
    char_end: int | None = Field(default=None, description="Document-global char end")


class ExtractedRelationship(BaseModel):
    source: str
    target: str
    type: str = Field(default="relates_to")
    description: str = ""


class ExtractionResult(BaseModel):
    entities: list[ExtractedEntity] = Field(default_factory=list)
    relationships: list[ExtractedRelationship] = Field(default_factory=list)


class GleanResult(BaseModel):
    missed_entities: list[ExtractedEntity] = Field(default_factory=list)
    missed_relationships: list[ExtractedRelationship] = Field(default_factory=list)
    reasoning: str = ""
