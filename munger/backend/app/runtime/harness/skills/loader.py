"""Load DeerFlow-format SKILL.md files for Munger agents."""

from __future__ import annotations

import logging
import re
from pathlib import Path

import yaml

from app.core.config import Settings
from app.runtime.harness.skills.types import SKILL_MD_FILE, Skill

logger = logging.getLogger(__name__)

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def _parse_allowed_tools(raw: object, skill_file: Path) -> list[str] | None:
    if raw is None:
        return None
    if not isinstance(raw, list):
        raise ValueError(f"allowed-tools in {skill_file} must be a list of strings")
    tools: list[str] = []
    for item in raw:
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"allowed-tools in {skill_file} must contain non-empty strings")
        tools.append(item.strip())
    return tools


def parse_skill_file(skill_file: Path) -> Skill | None:
    if not skill_file.exists() or skill_file.name != SKILL_MD_FILE:
        return None

    text = skill_file.read_text(encoding="utf-8")
    match = _FRONTMATTER_RE.match(text)
    if not match:
        logger.warning("Skill file missing YAML frontmatter: %s", skill_file)
        return None

    try:
        meta = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError as exc:
        logger.error("Invalid YAML in %s: %s", skill_file, exc)
        return None

    if not isinstance(meta, dict):
        return None

    name = str(meta.get("name") or skill_file.parent.name)
    description = str(meta.get("description") or "")
    allowed_tools = _parse_allowed_tools(meta.get("allowed-tools"), skill_file)
    tool_order = _parse_allowed_tools(meta.get("tool-order"), skill_file)
    content = text[match.end() :].strip()

    return Skill(
        name=name,
        description=description,
        content=content,
        allowed_tools=allowed_tools,
        skill_dir=skill_file.parent,
        tool_order=tool_order,
    )


def _skill_search_roots(settings: Settings) -> list[Path]:
    roots = [Path(settings.skills_dir)]
    builtin = Path(getattr(settings, "builtin_skills_dir", "/app/builtin-workflows"))
    if builtin not in roots:
        roots.append(builtin)
    return roots


def _resolve_skill_path(settings: Settings, skill_name: str) -> Path | None:
    relative_candidates = [
        skill_name,
        f"{skill_name}-ingest",
        "default-ingest" if skill_name in {"ingest", "default-ingest"} else None,
    ]
    for base in _skill_search_roots(settings):
        for rel in relative_candidates:
            if not rel:
                continue
            candidate = base / rel / SKILL_MD_FILE
            if candidate.exists():
                return candidate
    return None


def load_skill(settings: Settings, skill_name: str = "ingest") -> Skill:
    skill_path = _resolve_skill_path(settings, skill_name)
    if skill_path is None:
        raise FileNotFoundError(f"Skill not found: {skill_name} under {settings.skills_dir}")

    skill = parse_skill_file(skill_path)
    if skill is None:
        raise ValueError(f"Failed to parse skill: {skill_path}")
    return skill
