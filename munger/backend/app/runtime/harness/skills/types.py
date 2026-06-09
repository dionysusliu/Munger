"""Skill metadata types (DeerFlow-compatible)."""

from dataclasses import dataclass
from pathlib import Path

SKILL_MD_FILE = "SKILL.md"


@dataclass
class Skill:
    name: str
    description: str
    content: str
    allowed_tools: list[str] | None
    skill_dir: Path
    tool_order: list[str] | None = None
