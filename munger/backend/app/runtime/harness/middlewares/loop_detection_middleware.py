"""Detect repetitive tool call loops (simplified DeerFlow adaptation)."""

from __future__ import annotations

import hashlib
import json
import logging
from collections.abc import Awaitable, Callable
from typing import override

from langchain.agents import AgentState
from langchain.agents.middleware import AgentMiddleware
from langchain.agents.middleware.types import ModelCallResult, ModelRequest, ModelResponse
from langchain_core.messages import AIMessage, HumanMessage

logger = logging.getLogger(__name__)

_DEFAULT_WARN_THRESHOLD = 3
_DEFAULT_HARD_LIMIT = 5


class LoopDetectionMiddleware(AgentMiddleware[AgentState]):
    """Warn and eventually stop identical repeated tool calls."""

    def __init__(
        self,
        *,
        warn_threshold: int = _DEFAULT_WARN_THRESHOLD,
        hard_limit: int = _DEFAULT_HARD_LIMIT,
    ):
        self.warn_threshold = warn_threshold
        self.hard_limit = hard_limit
        self._counts: dict[str, int] = {}

    @staticmethod
    def _hash_tool_calls(message: AIMessage) -> list[str]:
        hashes: list[str] = []
        for tc in message.tool_calls or []:
            payload = json.dumps(
                {"name": tc.get("name"), "args": tc.get("args", {})},
                sort_keys=True,
                default=str,
            )
            hashes.append(hashlib.sha256(payload.encode()).hexdigest()[:16])
        return hashes

    @staticmethod
    def _messages_from_response(response: ModelResponse) -> list:
        return getattr(response, "result", None) or getattr(response, "messages", []) or []

    def _track_and_maybe_warn(self, response: ModelResponse) -> ModelResponse:
        messages = self._messages_from_response(response)
        ai_messages = [m for m in messages if isinstance(m, AIMessage)]
        if not ai_messages:
            return response

        last = ai_messages[-1]
        if not last.tool_calls:
            return response

        patched = last
        for digest in self._hash_tool_calls(last):
            self._counts[digest] = self._counts.get(digest, 0) + 1
            count = self._counts[digest]
            if count >= self.hard_limit:
                logger.warning("Loop detection hard limit reached for tool call hash %s", digest)
                patched = AIMessage(content=last.content or "Stopping due to repeated tool calls.")
                break
            if count >= self.warn_threshold:
                logger.warning("Loop detection warning for tool call hash %s (count=%s)", digest, count)

        if patched is not last:
            new_messages = list(messages)
            new_messages[-1] = patched
            return ModelResponse(result=new_messages)
        return response

    @override
    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelCallResult:
        return self._track_and_maybe_warn(handler(request))

    @override
    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelCallResult:
        response = await handler(request)
        return self._track_and_maybe_warn(response)
