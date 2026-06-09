"""Munger agent factory (DeerFlow create_deerflow_agent structure)."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from langchain.agents import create_agent
from langchain.agents.middleware import AgentMiddleware

from app.runtime.harness.middlewares import (
    DanglingToolCallMiddleware,
    LoopDetectionMiddleware,
    TokenUsageMiddleware,
    ToolErrorHandlingMiddleware,
)

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel
    from langchain_core.tools import BaseTool
    from langgraph.checkpoint.base import BaseCheckpointSaver
    from langgraph.graph.state import CompiledStateGraph

logger = logging.getLogger(__name__)


def build_ingest_middleware_chain() -> list[AgentMiddleware]:
    """Minimal middleware chain for ingest agent (no progressive tool gating)."""
    return [
        DanglingToolCallMiddleware(),
        ToolErrorHandlingMiddleware(),
        LoopDetectionMiddleware(),
        TokenUsageMiddleware(),
    ]


def create_munger_agent(
    model: BaseChatModel,
    tools: list[BaseTool],
    *,
    system_prompt: str,
    middleware: list[AgentMiddleware] | None = None,
    checkpointer: BaseCheckpointSaver | None = None,
    name: str = "ingest",
) -> CompiledStateGraph:
    """Create a Munger agent using LangChain create_agent."""
    effective_middleware = middleware or build_ingest_middleware_chain()
    return create_agent(
        model=model,
        tools=tools,
        middleware=effective_middleware,
        system_prompt=system_prompt,
        checkpointer=checkpointer,
        name=name,
    )
