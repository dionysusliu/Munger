"""Graph GC endpoints (SP2.4): candidates (HITL list) / prune-orphans / delete."""

from typing import Annotated

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.services.graph_gc_service import GraphGCService

router = APIRouter()


class DeleteRequest(BaseModel):
    # Explicit HITL deletion — may include mentioned entities by deliberate user choice.
    entity_ids: list[int] = Field(..., max_length=500)


@router.get("/candidates")
async def candidates_endpoint(max_mentions: Annotated[int, Query(ge=0, le=10)] = 1,
                              limit: Annotated[int, Query(ge=1, le=500)] = 100):
    cands = await GraphGCService(get_settings()).gc_candidates(max_mentions=max_mentions, limit=limit)
    return {"candidates": cands}


@router.post("/prune-orphans")
async def prune_orphans_endpoint():
    return await GraphGCService(get_settings()).prune_orphans()


@router.post("/delete")
async def delete_endpoint(req: DeleteRequest):
    return await GraphGCService(get_settings()).delete_entities(req.entity_ids)


@router.post("/retention")
async def retention_endpoint():
    """Age out ingest_events / chunk_extractions per RETENTION_* settings (0 = off)."""
    return await GraphGCService(get_settings()).purge_aged()
