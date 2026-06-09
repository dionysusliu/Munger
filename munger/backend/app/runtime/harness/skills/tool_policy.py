"""Filter tools by skill allowed-tools declarations (DeerFlow-compatible)."""

from __future__ import annotations

import logging
from typing import Protocol

from app.runtime.harness.skills.types import Skill

logger = logging.getLogger(__name__)


class NamedTool(Protocol):
    name: str


def allowed_tool_names_for_skills(skills: list[Skill]) -> set[str] | None:
    if not skills:
        return None

    allowed: set[str] = set()
    has_explicit = False
    for skill in skills:
        if skill.allowed_tools is None:
            continue
        has_explicit = True
        allowed.update(skill.allowed_tools)

    if not has_explicit:
        return None
    return allowed


def filter_tools_by_skill_allowed_tools[ToolT: NamedTool](tools: list[ToolT], skills: list[Skill]) -> list[ToolT]:
    allowed = allowed_tool_names_for_skills(skills)
    if allowed is None:
        return tools
    return [tool for tool in tools if tool.name in allowed]
