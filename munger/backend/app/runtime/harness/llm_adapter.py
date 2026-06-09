"""Wrap Munger LLMService as a LangChain BaseChatModel with tool-call support."""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.utils.function_calling import convert_to_openai_tool
from pydantic import ConfigDict, Field

from app.services.llm_service import LLMService, extract_assistant_message_text

logger = logging.getLogger(__name__)


def _message_to_dict(message: BaseMessage) -> dict:
    role = "user"
    if message.type == "ai":
        role = "assistant"
    elif message.type == "system":
        role = "system"
    elif message.type == "tool":
        role = "tool"

    payload: dict[str, Any] = {"role": role, "content": message.content or ""}
    if message.type == "ai" and getattr(message, "tool_calls", None):
        openai_tool_calls = []
        for tc in message.tool_calls:
            openai_tool_calls.append(
                {
                    "id": tc.get("id") or f"call_{uuid.uuid4().hex[:12]}",
                    "type": "function",
                    "function": {
                        "name": tc.get("name"),
                        "arguments": json.dumps(tc.get("args", {})),
                    },
                }
            )
        if openai_tool_calls:
            payload["tool_calls"] = openai_tool_calls
    if message.type == "tool":
        payload["tool_call_id"] = getattr(message, "tool_call_id", None)
        payload["name"] = getattr(message, "name", None)
    return payload


def _normalize_tool_calls(raw_calls: list[dict]) -> list[dict]:
    normalized: list[dict] = []
    for tc in raw_calls:
        fn = tc.get("function") or {}
        args_raw = fn.get("arguments", "{}")
        try:
            args = json.loads(args_raw) if isinstance(args_raw, str) else args_raw
        except json.JSONDecodeError:
            args = {}
        if not isinstance(args, dict):
            args = {}
        normalized.append(
            {
                "id": tc.get("id") or f"call_{uuid.uuid4().hex[:12]}",
                "name": fn.get("name") or "unknown",
                "args": args,
            }
        )
    return normalized


class MungerLLMChatModel(BaseChatModel):
    """LangChain chat model backed by Munger LLMService provider HTTP client."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    llm_service: Any = Field(exclude=True)
    temperature: float = 0.3
    max_tokens: int = 4096

    @property
    def _llm_type(self) -> str:
        return "munger-llm-service"

    def bind_tools(self, tools: list[Any], **kwargs: Any) -> "MungerLLMChatModel":
        """Return a copy with tools bound for create_agent tool-calling."""
        return self.bind(tools=tools, **kwargs)

    def _generate(self, messages: list[BaseMessage], stop: list[str] | None = None, **kwargs: Any) -> ChatResult:
        raise NotImplementedError("Use async generation via agenerate")

    async def _agenerate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        dict_messages = [_message_to_dict(m) for m in messages]
        tools = kwargs.get("tools") or []
        tool_defs = [convert_to_openai_tool(tool) for tool in tools] if tools else None

        provider = self.llm_service.provider
        client = provider._get_client()
        payload: dict[str, Any] = {
            "model": getattr(provider, "model", self.llm_service.settings.default_llm_model),
            "messages": dict_messages,
            "temperature": kwargs.get("temperature", self.temperature),
            "max_tokens": kwargs.get("max_tokens", self.max_tokens),
        }
        if tool_defs:
            payload["tools"] = tool_defs
            payload["tool_choice"] = "auto"

        response = await client.post("/chat/completions", json=payload)
        response.raise_for_status()
        data = response.json()
        message = data["choices"][0]["message"]
        content = extract_assistant_message_text(message)
        raw_tool_calls = message.get("tool_calls") or []

        if raw_tool_calls:
            ai_message = AIMessage(content=content or "", tool_calls=_normalize_tool_calls(raw_tool_calls))
        else:
            ai_message = AIMessage(content=content or "")

        usage = data.get("usage")
        if usage:
            ai_message.response_metadata = {"token_usage": usage}

        return ChatResult(generations=[ChatGeneration(message=ai_message)])
