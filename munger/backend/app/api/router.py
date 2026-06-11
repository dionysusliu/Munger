"""Main API router aggregator for Munger."""
from fastapi import APIRouter

from app.api import sources, wiki, entities, search, munger, config as config_api, retrieval, resolution, communities, chat, feedback, graph

api_router = APIRouter(prefix="/api")
api_router.include_router(sources.router, prefix="/sources", tags=["sources"])
api_router.include_router(wiki.router, prefix="/wiki", tags=["wiki"])
api_router.include_router(entities.router, prefix="/entities", tags=["entities"])
api_router.include_router(resolution.router, prefix="/entities", tags=["entities"])
api_router.include_router(search.router, prefix="/search", tags=["search"])
api_router.include_router(retrieval.router, prefix="/search", tags=["search"])
api_router.include_router(munger.router, prefix="/munger", tags=["munger"])
api_router.include_router(config_api.router, prefix="/config", tags=["config"])
api_router.include_router(communities.router, prefix="/communities", tags=["communities"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(feedback.router, prefix="/feedback", tags=["feedback"])
api_router.include_router(graph.router, prefix="/graph", tags=["graph"])
