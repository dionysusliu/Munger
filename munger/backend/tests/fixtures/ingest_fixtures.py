"""Scripted RuntimeServices builder for deterministic ingest graph tests."""

from __future__ import annotations

from typing import Any

from app.core.config import Settings
from app.runtime.context import RuntimeServices
from tests.fixtures.fake_llm import ScriptedLLMService


def scripted_services(
    scripts: list[dict[str, Any]],
    settings: Settings | None = None,
) -> RuntimeServices:
    """Return a fully-wired RuntimeServices backed by ScriptedLLMService.

    Uses RuntimeServices.from_settings so every service is constructed with
    the real signature; only the LLM is replaced with the scripted stub.
    """
    settings = settings or Settings(
        ingest_orchestrator="graph",
        ingest_map_mode="service",
    )
    llm = ScriptedLLMService(scripts=scripts)
    return RuntimeServices.from_settings(settings, llm=llm)


def two_entity_scripts() -> list[dict[str, Any]]:
    """One round-0 extraction dict: Charlie Munger / Mental Models / advocates."""
    return [
        {
            "entities": [
                {
                    "name": "Charlie Munger",
                    "type": "person",
                    "description": "Investor",
                    "char_start": 0,
                    "char_end": 14,
                },
                {
                    "name": "Mental Models",
                    "type": "concept",
                    "description": "Latticework of models",
                    "char_start": 20,
                    "char_end": 33,
                },
            ],
            "relationships": [
                {
                    "source": "Charlie Munger",
                    "target": "Mental Models",
                    "type": "advocates",
                    "description": "promotes",
                },
            ],
        },
    ]
