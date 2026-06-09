"""Log token usage from model responses."""

from __future__ import annotations

import logging
from typing import override

from langchain.agents import AgentState
from langchain.agents.middleware import AgentMiddleware
from langchain.agents.middleware.types import ModelCallResult, ModelRequest, ModelResponse
from langchain_core.messages import AIMessage

logger = logging.getLogger(__name__)


class TokenUsageMiddleware(AgentMiddleware[AgentState]):
    """Log token usage metadata when present on AIMessage responses."""

    @staticmethod
    def _messages_from_response(response: ModelResponse) -> list:
        return getattr(response, "result", None) or getattr(response, "messages", []) or []

    def _log_usage(self, response: ModelResponse) -> ModelResponse:
        for message in self._messages_from_response(response):
            if not isinstance(message, AIMessage):
                continue
            usage = getattr(message, "usage_metadata", None) or {}
            if usage:
                logger.info(
                    "Token usage: input=%s output=%s total=%s",
                    usage.get("input_tokens"),
                    usage.get("output_tokens"),
                    usage.get("total_tokens"),
                )
            response_meta = getattr(message, "response_metadata", None) or {}
            token_usage = response_meta.get("token_usage")
            if token_usage:
                logger.info("Token usage (response_metadata): %s", token_usage)
        return response

    @override
    def wrap_model_call(
        self,
        request: ModelRequest,
        handler,
    ) -> ModelCallResult:
        return self._log_usage(handler(request))

    @override
    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler,
    ) -> ModelCallResult:
        response = await handler(request)
        return self._log_usage(response)
