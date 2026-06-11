"""Centralized prompt module — single source of truth for all LLM prompt text."""

from app.prompts.extraction import (
    EXTRACT_SYSTEM,
    GLEAN_SYSTEM,
    GLEAN_YES_NO_SYSTEM,
)
from app.prompts.ontology import (
    ALIAS_TYPE_MAPPING,
    ENTITY_TYPE_NAMES,
    ENTITY_TYPES,
    LEGACY_TYPE_MAPPING,
    NAMING_RULES,
    TYPE_PRIORITY,
    ontology_block,
)
from app.prompts.resolution import PROF_MERGE_SYSTEM, SAME_ENTITY_SYSTEM
from app.prompts.wiki import (
    FORMULA_RULES,
    GROUNDING_RULES,
    SUGGEST_LINKS_SYSTEM,
    WIKI_TYPE_PROMPTS,
    WIKILINK_RULES,
    build_wiki_system,
)

__all__ = [
    "ALIAS_TYPE_MAPPING",
    "ENTITY_TYPE_NAMES",
    "ENTITY_TYPES",
    "EXTRACT_SYSTEM",
    "FORMULA_RULES",
    "GLEAN_SYSTEM",
    "GLEAN_YES_NO_SYSTEM",
    "GROUNDING_RULES",
    "LEGACY_TYPE_MAPPING",
    "NAMING_RULES",
    "PROF_MERGE_SYSTEM",
    "SAME_ENTITY_SYSTEM",
    "SUGGEST_LINKS_SYSTEM",
    "TYPE_PRIORITY",
    "WIKILINK_RULES",
    "WIKI_TYPE_PROMPTS",
    "build_wiki_system",
    "ontology_block",
]
