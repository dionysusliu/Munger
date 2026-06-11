"""Community-report endpoints (SP2.3b): generate reports + thematic search."""

from typing import Annotated

from fastapi import APIRouter, Query

from app.core.config import get_settings
from app.services.community_report_service import CommunityReportService
from app.services.llm_service import LLMService

router = APIRouter()


@router.post("/reports")
async def reports_endpoint(min_size: int = 3, top_members: int = 15):
    settings = get_settings()
    service = CommunityReportService(settings, llm_service=LLMService(settings))
    return await service.generate_reports(min_size=min_size, top_members=top_members)


@router.get("/search")
async def search_endpoint(
    q: Annotated[str, Query(min_length=1)],
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
):
    settings = get_settings()
    service = CommunityReportService(settings, llm_service=None)
    results = await service.community_search(q, limit=limit)
    return {"query": q, "results": results}
