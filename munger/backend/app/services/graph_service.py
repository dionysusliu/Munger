"""Graph-global signals over entity_edges, NetworkX-backed.

The analytics surface mirrors txtai's Graph component (``pagerank``,
``communities``; ``showpath`` / ``centrality`` will land in SP4 for cross-domain
bridging). Implemented over an in-memory NetworkX graph built from ``entity_edges``
and persisted to Postgres (``entities.salience`` / ``entities.community_id`` +
``communities``). NetworkX is chosen for maturity + ecosystem; at extreme scale a
faster backend (rustworkx/igraph) can be swapped behind this interface.
"""

from __future__ import annotations

import networkx as nx
from sqlalchemy import text, update

from app.core.config import Settings, get_settings
from app.core.database import async_session_maker
from app.models.community import Community
from app.models.entity import Entity


class GraphService:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()

    async def _build_graph(self) -> tuple[nx.Graph, list[int]]:
        """Load all entities (nodes) + entity_edges (weighted edges) into NetworkX."""
        async with async_session_maker() as session:
            entity_ids = [
                r[0] for r in (await session.execute(text("SELECT id FROM entities ORDER BY id"))).all()
            ]
            edge_rows = (
                await session.execute(
                    text("SELECT src_entity_id, tgt_entity_id, weight FROM entity_edges")
                )
            ).all()
        g = nx.Graph()
        g.add_nodes_from(entity_ids)
        g.add_weighted_edges_from([(s, t, float(w)) for (s, t, w) in edge_rows])
        return g, entity_ids

    @staticmethod
    def pagerank(g: nx.Graph) -> dict[int, float]:
        """PageRank centrality per node = entity salience (mirrors txtai Graph.pagerank())."""
        if g.number_of_edges() == 0:
            return {n: 0.0 for n in g.nodes}
        return nx.pagerank(g, weight="weight")

    @staticmethod
    def communities(g: nx.Graph, seed: int = 42) -> list[set[int]]:
        """Single-level Louvain communities, deterministic via seed (mirrors txtai Graph.communities())."""
        if g.number_of_nodes() == 0:
            return []
        return nx.community.louvain_communities(g, weight="weight", seed=seed)

    async def personalized_pagerank(self, seeds: dict[int, float]) -> dict[int, float]:
        """Seed-biased PageRank over entity_edges. `seeds` maps entity_id -> weight.

        Returns {} when there are no nodes or no seed mass lands on a graph node.
        """
        if not seeds:
            return {}
        g, _ = await self._build_graph()
        if g.number_of_nodes() == 0:
            return {}
        personalization = {n: float(seeds.get(n, 0.0)) for n in g.nodes}
        if sum(personalization.values()) == 0.0:
            return {}
        weight = "weight" if g.number_of_edges() else None
        return nx.pagerank(g, weight=weight, personalization=personalization)

    async def shortest_path(self, source: int, target: int) -> list[int]:
        """Fewest-hop path of entity ids from source to target over entity_edges (the bridge).

        Returns [] when either node is absent or the two are disconnected.
        """
        if source == target:
            return [source]
        g, _ = await self._build_graph()
        if source not in g or target not in g:
            return []
        try:
            return nx.shortest_path(g, source=source, target=target)
        except nx.NetworkXNoPath:
            return []

    async def recompute(self) -> dict:
        """Full recompute of entities.salience (PageRank) + entities.community_id (Louvain).

        Global + deterministic; offline (not wired to per-source ingest).
        """
        g, entity_ids = await self._build_graph()
        if not entity_ids:
            return {"entities": 0, "communities": 0}

        salience = self.pagerank(g)
        comms = self.communities(g)
        node_to_comm: dict[int, int] = {n: cidx for cidx, members in enumerate(comms) for n in members}

        async with async_session_maker() as session:
            await session.execute(text("DELETE FROM communities"))
            cluster_to_id: dict[int, int] = {}
            for cidx, members in enumerate(comms):
                comm = Community(level=0, size=len(members))
                session.add(comm)
                await session.flush()
                cluster_to_id[cidx] = comm.id
            for eid in entity_ids:
                cidx = node_to_comm.get(eid)
                await session.execute(
                    update(Entity)
                    .where(Entity.id == eid)
                    .values(
                        salience=float(salience.get(eid, 0.0)),
                        community_id=cluster_to_id.get(cidx) if cidx is not None else None,
                    )
                )
            await session.commit()

        return {"entities": len(entity_ids), "communities": len(comms)}
