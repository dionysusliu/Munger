"""Chat-over-retrieval endpoints (SP4.1)."""

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import get_settings
from app.services.chat_service import ChatService
from app.services.llm_service import LLMService

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    session_id: int | None = None


def _service(with_llm: bool = True) -> ChatService:
    settings = get_settings()
    return ChatService(settings, llm_service=LLMService(settings) if with_llm else None)


@router.post("")
async def chat_endpoint(req: ChatRequest):
    svc = _service(with_llm=True)
    session_id = req.session_id or await svc.create_session()
    return await svc.ask(session_id, req.message)


@router.post("/sessions")
async def create_session_endpoint(title: str | None = None):
    return {"session_id": await _service(with_llm=False).create_session(title)}


@router.get("/sessions/{session_id}/messages")
async def messages_endpoint(session_id: int):
    return {"session_id": session_id, "messages": await _service(with_llm=False).messages(session_id)}
