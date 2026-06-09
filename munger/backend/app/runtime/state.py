"""Typed state contract for the ingest LangGraph."""

from typing import TypedDict


class EntityRef(TypedDict, total=False):
    id: int
    name: str
    entity_type: str
    wiki_page_id: int | None


class IngestRunState(TypedDict, total=False):
    source_id: int
    text: str
    summary: str
    entities: list[EntityRef]
    wiki_page_ids: list[int]
    error: str | None
    status: str
    entity_count: int
