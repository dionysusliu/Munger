"""Scripted LLM responses for deterministic ingest tests."""

from __future__ import annotations

import json
from typing import Any

from app.schemas.extraction import ExtractionResult, GleanResult
from app.services.llm_service import LLMService


class ScriptedLLMService:
    """Minimal LLM stub returning canned extraction/glean JSON."""

    def __init__(self, scripts: list[str | dict[str, Any]] | None = None):
        self._scripts = list(scripts or [])
        self._call_index = 0

    async def chat(self, messages: list[dict], **kwargs) -> str:
        if self._call_index >= len(self._scripts):
            return json.dumps({"entities": [], "relationships": []})
        script = self._scripts[self._call_index]
        self._call_index += 1
        if isinstance(script, str):
            return script
        return json.dumps(script)

    async def chat_structured(self, messages: list[dict], response_model: type, **kwargs):
        raw = await self.chat(messages, **kwargs)
        data = json.loads(raw) if isinstance(raw, str) else raw
        return response_model.model_validate(data)

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [[0.1] * 768 for _ in texts]

    async def embed_text(self, text: str) -> list[float]:
        return (await self.embed_texts([text]))[0]

    async def summarize(self, text: str, max_length: int = 1000) -> str:
        return "Summary"

    async def generate_wiki_page(self, title: str, content: str, page_type: str = "entity") -> str:
        return f"# {title}\n\n{content[:200]}"


def cross_chunk_extraction_scripts() -> list[dict[str, Any]]:
    """Two-chunk corpus: Charlie Munger / Munger variants for linking tests."""
    return [
        {
            "entities": [
                {
                    "name": "Charlie Munger",
                    "type": "person",
                    "description": "Investor",
                    "char_start": 0,
                    "char_end": 14,
                }
            ],
            "relationships": [],
        },
        {
            "entities": [
                {
                    "name": "Munger",
                    "type": "person",
                    "description": "Partner of Buffett",
                    "char_start": 20,
                    "char_end": 26,
                }
            ],
            "relationships": [],
        },
    ]
