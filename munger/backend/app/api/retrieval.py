"""Entity-centric retrieval endpoint (SP3.1)."""

from fastapi import APIRouter, Query

from app.core.config import get_settings
from app.services.llm_service import LLMService
from app.services.retrieval_service import RetrievalService

router = APIRouter()


@router.get("/retrieve")
async def retrieve(q: str = Query(..., min_length=1), k: int = Query(20, ge=1, le=100)):
    settings = get_settings()
    service = RetrievalService(settings, llm_service=LLMService(settings))
    results = await service.search(q, k=k)
    return {"query": q, "results": results}
