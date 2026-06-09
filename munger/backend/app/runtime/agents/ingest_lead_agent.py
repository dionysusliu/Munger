"""Ingest agent factory without progressive tool gating."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.runtime.agents.ingest_prompt import build_ingest_prompt
from app.runtime.context import RuntimeServices
from app.runtime.harness.factory import build_ingest_middleware_chain, create_munger_agent
from app.runtime.harness.llm_adapter import MungerLLMChatModel
from app.runtime.harness.skills.loader import load_skill
from app.runtime.harness.skills.tool_policy import filter_tools_by_skill_allowed_tools
from app.runtime.tools.ingest_tools import build_ingest_tools

if TYPE_CHECKING:
    from langgraph.graph.state import CompiledStateGraph

logger = logging.getLogger(__name__)


def make_ingest_lead_agent(
    services: RuntimeServices,
    checkpointer,
    *,
    job_id: int | None = None,
    skill_name: str = "ingest",
) -> CompiledStateGraph:
    if not services.llm:
        raise RuntimeError("LLM service is required for ingest lead agent")

    skill = load_skill(services.settings, skill_name)
    tools = build_ingest_tools(services, job_id=job_id)
    tools = filter_tools_by_skill_allowed_tools(tools, [skill])
    model = MungerLLMChatModel(llm_service=services.llm)
    system_prompt = build_ingest_prompt(skill)

    return create_munger_agent(
        model=model,
        tools=tools,
        system_prompt=system_prompt,
        checkpointer=checkpointer,
        middleware=build_ingest_middleware_chain(),
        name="ingest",
    )
