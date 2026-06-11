"""Graph maintenance endpoints: recompute salience + communities (backfill-friendly)."""

from typing import Annotated

from fastapi import APIRouter, Query

from app.core.config import get_settings
from app.services.edge_service import EdgeService
from app.services.graph_service import GraphService

router = APIRouter()


@router.post("/recompute")
async def recompute_endpoint(rebuild_edges: Annotated[bool, Query()] = True):
    """Rebuild entity_edges (optional) then recompute PageRank salience + Louvain communities.

    The backfill entry point for pre-existing data: edges/salience/communities are derived
    layers that only populate via the per-source finalize hook on NEW ingests."""
    settings = get_settings()
    edges = await EdgeService(settings).rebuild_all() if rebuild_edges else None
    stats = await GraphService(settings).recompute()
    return {**stats, "edges": edges}
