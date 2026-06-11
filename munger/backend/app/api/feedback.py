"""HITL feedback endpoints (SP4.2): merge / relate / rate."""

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import get_settings
from app.services.feedback_service import FeedbackService

router = APIRouter()


class MergeFeedback(BaseModel):
    entity_a_id: int
    entity_b_id: int
    same: bool
    note: str | None = None


class RelateFeedback(BaseModel):
    entity_a_id: int
    entity_b_id: int
    relationship_type: str = "related"
    note: str | None = None


class RateFeedback(BaseModel):
    message_id: int
    rating: Literal[1, -1]
    note: str | None = None


@router.post("/merge")
async def merge_endpoint(req: MergeFeedback):
    return await FeedbackService(get_settings()).merge_feedback(
        req.entity_a_id, req.entity_b_id, req.same, req.note)


@router.post("/relate")
async def relate_endpoint(req: RelateFeedback):
    return await FeedbackService(get_settings()).relate_feedback(
        req.entity_a_id, req.entity_b_id, req.relationship_type, req.note)


@router.post("/rate")
async def rate_endpoint(req: RateFeedback):
    updated = await FeedbackService(get_settings()).rate_message(req.message_id, req.rating, req.note)
    return {"updated": updated}
