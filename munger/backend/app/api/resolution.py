"""Entity-resolution endpoints (SP2.2): resolve / unmerge / label."""

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import get_settings
from app.services.edge_service import EdgeService
from app.services.entity_resolution_service import EntityResolutionService

router = APIRouter()


class UnmergeRequest(BaseModel):
    entity_id: int


class LabelRequest(BaseModel):
    entity_a_id: int
    entity_b_id: int
    label: str  # "match" | "reject"
    note: str | None = None


@router.post("/resolve")
async def resolve_endpoint(tau_block: float = 0.4, tau_auto: float = 0.85):
    settings = get_settings()
    stats = await EntityResolutionService(settings).resolve(tau_block=tau_block, tau_auto=tau_auto)
    await EdgeService(settings).rebuild_all()
    return stats


@router.post("/unmerge")
async def unmerge_endpoint(req: UnmergeRequest):
    settings = get_settings()
    cleared = await EntityResolutionService(settings).unmerge(req.entity_id)
    await EdgeService(settings).rebuild_all()
    return {"cleared": cleared}


@router.post("/label")
async def label_pair_endpoint(req: LabelRequest):
    await EntityResolutionService(get_settings()).label_pair(
        req.entity_a_id, req.entity_b_id, req.label, req.note)
    return {"ok": True}
