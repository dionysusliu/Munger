"""Chat-over-retrieval endpoints (SP4.1)."""

import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
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


@router.post("/stream")
async def chat_stream_endpoint(req: ChatRequest):
    svc = _service(with_llm=True)
    session_id = req.session_id or await svc.create_session()

    async def _frames():
        try:
            async for event in svc.ask_stream(session_id, req.message):
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as exc:  # surface the error as a terminal SSE frame
            yield f"data: {json.dumps({'type': 'error', 'detail': str(exc)[:300]})}\n\n"

    return StreamingResponse(_frames(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


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


@router.get("/sessions")
async def list_sessions_endpoint():
    return {"sessions": await _service(with_llm=False).list_sessions()}


@router.delete("/sessions/{session_id}")
async def delete_session_endpoint(session_id: int):
    return {"deleted": await _service(with_llm=False).delete_session(session_id)}
