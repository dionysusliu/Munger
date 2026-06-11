"""Conservative RAG chat over the knowledge graph: retrieve -> bridge -> synthesize -> persist.

Read-only (no graph write-back — that is SP4.2). Grounds answers in RetrievalService results
and surfaces a cross-domain bridge (shortest path between the top-2 retrieved entities)."""

from __future__ import annotations

import json

from sqlalchemy import text

from app.core.config import Settings, get_settings
from app.core.database import async_session_maker
from app.services.graph_service import GraphService
from app.services.retrieval_service import RetrievalService

_SYSTEM = (
    "You are Munger, a knowledge assistant over a personal knowledge graph. "
    "Answer using ONLY the provided context entities; cite them by name. "
    "If a cross-domain bridge path is provided, explain that connection (the 'latticework'). "
    "Be conservative: if the context does not cover the question, say so plainly."
)


class ChatService:
    def __init__(self, settings: Settings | None = None, llm_service=None,
                 retrieval: RetrievalService | None = None, graph: GraphService | None = None):
        self.settings = settings or get_settings()
        self.llm = llm_service
        self.retrieval = retrieval or RetrievalService(self.settings, llm_service=llm_service)
        self.graph = graph or GraphService(self.settings)

    async def create_session(self, title: str | None = None) -> int:
        async with async_session_maker() as s:
            row = (await s.execute(
                text("INSERT INTO chat_sessions (title) VALUES (:t) RETURNING id"), {"t": title})).first()
            await s.commit()
            return row[0]

    async def _history(self, session_id: int, limit: int = 10) -> list[dict]:
        async with async_session_maker() as s:
            rows = (await s.execute(
                text("SELECT role, content FROM chat_messages WHERE session_id = :sid ORDER BY id DESC LIMIT :l"),
                {"sid": session_id, "l": limit})).all()
        return [{"role": r[0], "content": r[1]} for r in reversed(rows)]

    @staticmethod
    def _format_context(results: list[dict], bridge_names: list[str]) -> str:
        lines = ["Context entities:"]
        for r in results:
            lines.append(f"- {r['name']} ({r['entity_type']}): {(r.get('description') or '')[:200]}")
        if bridge_names:
            lines.append("Cross-domain bridge: " + " -> ".join(bridge_names))
        return "\n".join(lines)

    async def _entity_names(self, ids: list[int]) -> dict[int, str]:
        if not ids:
            return {}
        async with async_session_maker() as s:
            rows = (await s.execute(
                text("SELECT id, name FROM entities WHERE id = ANY(:ids)"), {"ids": ids})).all()
        return {r[0]: r[1] for r in rows}

    async def ask(self, session_id: int, message: str, k: int = 8) -> dict:
        results = await self.retrieval.search(message, k=k)

        bridge: list[int] = []
        if len(results) >= 2:
            bridge = await self.graph.shortest_path(results[0]["entity_id"], results[1]["entity_id"])
        name_map = await self._entity_names(bridge)
        bridge_names = [name_map.get(b, str(b)) for b in bridge]

        history = await self._history(session_id)
        context = self._format_context(results, bridge_names)
        messages = [{"role": "system", "content": f"{_SYSTEM}\n\n{context}"}] + history + [
            {"role": "user", "content": message}]
        answer = await self.llm.chat(messages)

        citations = [{"entity_id": r["entity_id"], "name": r["name"], "wiki": r.get("wiki")} for r in results]
        await self._persist(session_id, message, answer, citations, bridge)
        return {"session_id": session_id, "answer": answer, "citations": citations, "bridge": bridge}

    async def _persist(self, session_id: int, user_msg: str, answer: str,
                       citations: list[dict], bridge: list[int]) -> None:
        async with async_session_maker() as s:
            await s.execute(
                text("INSERT INTO chat_messages (session_id, role, content) VALUES (:sid, 'user', :c)"),
                {"sid": session_id, "c": user_msg})
            await s.execute(
                text("INSERT INTO chat_messages (session_id, role, content, citations) "
                     "VALUES (:sid, 'assistant', :c, :cit)"),
                {"sid": session_id, "c": answer,
                 "cit": json.dumps({"citations": citations, "bridge": bridge})})
            await s.commit()

    async def messages(self, session_id: int) -> list[dict]:
        async with async_session_maker() as s:
            rows = (await s.execute(
                text("SELECT role, content, citations FROM chat_messages WHERE session_id = :sid ORDER BY id"),
                {"sid": session_id})).all()
        return [{"role": r[0], "content": r[1], "meta": json.loads(r[2]) if r[2] else None} for r in rows]
