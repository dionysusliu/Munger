"""Persist ingest timeline events."""

from __future__ import annotations

import json
import logging
from typing import Any

from app.core.database import async_session_maker
from app.models.ingest_event import IngestEvent

logger = logging.getLogger(__name__)

MAX_PAYLOAD_CHARS = 4096


def _truncate(value: Any) -> Any:
    if isinstance(value, str) and len(value) > MAX_PAYLOAD_CHARS:
        return value[:MAX_PAYLOAD_CHARS] + "…[truncated]"
    if isinstance(value, dict):
        return {k: _truncate(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_truncate(v) for v in value]
    return value


async def record_ingest_event(
    *,
    source_id: int,
    event_type: str,
    payload: dict[str, Any] | None = None,
    job_id: int | None = None,
) -> None:
    safe_payload = _truncate(payload or {})
    try:
        async with async_session_maker() as session:
            session.add(
                IngestEvent(
                    source_id=source_id,
                    job_id=job_id,
                    event_type=event_type,
                    payload=safe_payload,
                )
            )
            await session.commit()
    except Exception:
        logger.exception("Failed to record ingest event for source %s", source_id)


def serialize_langchain_message(message: Any) -> dict[str, Any]:
    content = getattr(message, "content", "") or ""
    if not isinstance(content, str):
        try:
            content = json.dumps(content, default=str)
        except Exception:
            content = str(content)
    data: dict[str, Any] = {"content": content, "type": getattr(message, "type", "unknown")}
    tool_calls = getattr(message, "tool_calls", None)
    if tool_calls:
        data["tool_calls"] = [
            {"id": tc.get("id"), "name": tc.get("name"), "args": tc.get("args", {})}
            for tc in tool_calls
        ]
    if getattr(message, "type", "") == "tool":
        data["tool_call_id"] = getattr(message, "tool_call_id", None)
        data["name"] = getattr(message, "name", None)
    return data
