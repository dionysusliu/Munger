"""System prompt builder for the ingest lead agent."""

from __future__ import annotations

from app.runtime.harness.skills.types import Skill
from app.runtime.pipeline_events import INGEST_TOOL_ORDER


def build_ingest_prompt(skill: Skill) -> str:
    allowed = ", ".join(skill.allowed_tools or [])
    order = skill.tool_order or INGEST_TOOL_ORDER
    order_text = " → ".join(order)
    return f"""You are the Munger ingest lead agent. Process uploaded sources into entities and wiki pages.

## Skill: {skill.name}
{skill.description}

## Allowed tools
{allowed}

## Execution policy
1. Call tools in this exact order, one at a time:
   {order_text}
2. Each tool accepts only `source_id` — never pass text, summaries, or entities as arguments.
3. If parse_document fails, stop immediately.
4. Summarize/entity/wiki failures are non-fatal — continue to the next step when possible.
5. After finalize_ingest succeeds, respond with a brief completion summary.

## Skill guidance
{skill.content}
"""
