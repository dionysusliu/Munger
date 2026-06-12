"""Munger - FastAPI application entry point.

Munger is an automated knowledge base system inspired by Andrej Karpathy's
LLM Wiki and Charlie Munger's multi-dimensional thinking framework.
"""
import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db, async_session_maker
from app.api.router import api_router
from app.models.source import Source
from app.models.wiki import WikiPage, WikiLink
from app.models.entity import Entity
from app.models.munger import MungerAnalysis
from app.models.log import IngestionLog
from app.models.config import Config
from app.schemas.common import StatsResponse

settings = get_settings()


# ---------------------------------------------------------------------------
# Lifespan (startup/shutdown)
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler - startup and shutdown logic."""
    # --- Startup ---
    from app.db.migrate import run_migrations
    from app.observability.langsmith_setup import configure_langsmith
    from app.core.database import engine
    from app.observability.otel_setup import setup_otel

    configure_langsmith(settings)
    run_migrations()
    setup_otel("munger-backend", app=app, sqlalchemy_engine=engine)

    # Ensure data directories exist
    for directory in [settings.data_dir, settings.sources_dir, settings.wiki_dir, settings.schema_dir]:
        os.makedirs(directory, exist_ok=True)

    # Ensure default config entries exist
    async with async_session_maker() as session:
        result = await session.execute(select(Config))
        existing = result.scalars().all()
        if not existing:
            default_configs = [
                Config(key="llm.default_provider", value=settings.default_llm_provider,
                       description="Default LLM provider"),
                Config(key="llm.default_model", value=settings.default_llm_model,
                       description="Default LLM model"),
                Config(key="llm.embedding_model", value=settings.embedding_model,
                       description="Embedding model"),
                Config(key="llm.max_context_tokens", value=str(settings.max_context_tokens),
                       description="Max context tokens"),
                Config(key="ingest.auto_analyze", value="true",
                       description="Auto-run Munger analysis after ingestion"),
                Config(key="ingest.auto_create_wiki", value="true",
                       description="Auto-create wiki pages during ingestion"),
            ]
            for cfg in default_configs:
                session.add(cfg)
            await session.commit()

    yield

    # --- Shutdown ---
    # Cleanup if needed


# ---------------------------------------------------------------------------
# FastAPI Application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Munger API",
    description=(
        "Automated knowledge base with Munger thinking framework.\n\n"
        "Munger incrementally ingests source materials, extracts entities "
        "and concepts, and maintains an interconnected wiki through "
        "LLM-powered 12-dimension analysis."
    ),
    version=settings.app_version,
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router)


# ---------------------------------------------------------------------------
# Root & Health
# ---------------------------------------------------------------------------

@app.get("/", include_in_schema=False)
async def root():
    """Redirect root to API health check."""
    return {
        "name": "Munger API",
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/api/health",
    }


@app.get("/api/health")
async def health_check():
    """Health check endpoint.

    Returns basic system status and version information.
    """
    return {
        "status": "healthy",
        "version": settings.app_version,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------

@app.get("/api/stats")
async def get_stats(db: AsyncSession = Depends(get_db)):
    """System statistics dashboard.

    Returns counts of sources, wiki pages, entities, and links,
    along with breakdowns by type and recent activity.
    """
    # Total counts
    source_count_result = await db.execute(select(func.count(Source.id)))
    total_sources = source_count_result.scalar()

    wiki_count_result = await db.execute(select(func.count(WikiPage.id)))
    total_wiki_pages = wiki_count_result.scalar()

    entity_count_result = await db.execute(select(func.count(Entity.id)))
    total_entities = entity_count_result.scalar()

    link_count_result = await db.execute(select(func.count(WikiLink.id)))
    total_links = link_count_result.scalar()

    # Recent counts (last 7 days)
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)

    recent_sources_result = await db.execute(
        select(func.count(Source.id)).where(Source.created_at >= week_ago)
    )
    recent_sources = recent_sources_result.scalar()

    recent_wiki_result = await db.execute(
        select(func.count(WikiPage.id)).where(WikiPage.created_at >= week_ago)
    )
    recent_wiki_pages = recent_wiki_result.scalar()

    # Breakdowns by type
    sources_by_type = {}
    source_type_result = await db.execute(
        select(Source.file_type, func.count(Source.id))
        .group_by(Source.file_type)
    )
    for row in source_type_result.all():
        sources_by_type[row[0]] = row[1]

    wiki_by_type = {}
    wiki_type_result = await db.execute(
        select(WikiPage.page_type, func.count(WikiPage.id))
        .group_by(WikiPage.page_type)
    )
    for row in wiki_type_result.all():
        wiki_by_type[row[0]] = row[1]

    entities_by_type = {}
    entity_type_result = await db.execute(
        select(Entity.entity_type, func.count(Entity.id))
        .group_by(Entity.entity_type)
    )
    for row in entity_type_result.all():
        entities_by_type[row[0]] = row[1]

    # Recent activity logs
    recent_logs_result = await db.execute(
        select(IngestionLog)
        .order_by(desc(IngestionLog.created_at))
        .limit(10)
    )
    recent_logs = recent_logs_result.scalars().all()

    # Source status breakdown
    status_breakdown = {}
    status_result = await db.execute(
        select(Source.status, func.count(Source.id))
        .group_by(Source.status)
    )
    for row in status_result.all():
        status_breakdown[row[0]] = row[1]

    return {
        "total_sources": total_sources,
        "total_wiki_pages": total_wiki_pages,
        "total_entities": total_entities,
        "total_links": total_links,
        "recent_sources": recent_sources,
        "recent_wiki_pages": recent_wiki_pages,
        "sources_by_type": sources_by_type,
        "wiki_pages_by_type": wiki_by_type,
        "entities_by_type": entities_by_type,
        "source_status_breakdown": status_breakdown,
        "recent_activity": [
            {
                "id": log.id,
                "action": log.action,
                "log_type": log.log_type,
                "created_at": log.created_at,
            }
            for log in recent_logs
        ],
    }


# ---------------------------------------------------------------------------
# Global Exception Handler
# ---------------------------------------------------------------------------

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Handle unexpected exceptions gracefully."""
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "type": type(exc).__name__,
        },
    )
