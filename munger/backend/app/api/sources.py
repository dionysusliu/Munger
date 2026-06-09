"""Source management API routes for Munger."""
import hashlib
import os
from datetime import datetime
from typing import Optional

import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form, status
from fastapi.responses import JSONResponse
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.config import get_settings
from app.models.source import Source
from app.models.wiki import WikiPage
from app.models.munger import MungerAnalysis
from app.models.log import IngestionLog
from app.schemas.source import SourceResponse, SourceList
from app.models.chunk import Chunk
from app.models.chunk_extraction import ChunkExtraction
from app.models.entity import Entity, EntityMention
from app.models.entity_relationship import EntityRelationship
from app.models.ingest_event import IngestEvent
from app.models.ingest_job import IngestJob
from app.services.ingest_job_service import enqueue_ingest_job, get_active_job

router = APIRouter()
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _compute_file_hash(content: bytes) -> str:
    """Compute SHA-256 hash of file content."""
    return hashlib.sha256(content).hexdigest()


def _get_storage_path(filename: str, data_dir: str) -> str:
    """Build a year/month-based relative storage path for a source file."""
    now = datetime.utcnow()
    year = now.strftime("%Y")
    month = now.strftime("%m")
    directory = Path(data_dir) / "sources" / year / month
    directory.mkdir(parents=True, exist_ok=True)

    base = Path(filename).stem or "untitled"
    ext = Path(filename).suffix
    candidate = f"{base}{ext}"
    counter = 1

    while (directory / candidate).exists():
        candidate = f"{base}_{counter:03d}{ext}"
        counter += 1

    return str(Path("sources") / year / month / candidate)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/upload", response_model=SourceResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
):
    """Upload a file (PDF, TXT, MD) and create a Source record.

    The file is saved to the sources storage directory and a SHA-256 hash is
    computed. The source is created with status ``pending`` so the ingestion
    pipeline can pick it up.
    """
    from app.core.config import get_settings
    settings = get_settings()

    # Read file content
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")

    # Compute hash and determine file type
    content_hash = _compute_file_hash(content)
    filename = file.filename or "untitled"
    file_ext = os.path.splitext(filename)[1].lower().lstrip(".")

    # Determine file_type from extension
    ext_to_type = {
        "pdf": "pdf",
        "txt": "txt",
        "md": "md",
        "markdown": "md",
        "html": "html",
        "htm": "html",
    }
    file_type = ext_to_type.get(file_ext, "unknown")

    # Check for duplicate by hash
    existing = await db.execute(
        select(Source).where(Source.content_hash == content_hash)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A source with identical content already exists",
        )

    # Build storage path after duplicate validation so rejected uploads
    # never mutate an existing artifact on disk.
    rel_path = _get_storage_path(filename, settings.data_dir)
    abs_path = os.path.join(settings.data_dir, rel_path)

    with open(abs_path, "wb") as f:
        f.write(content)

    # Create Source record
    source = Source(
        title=title or filename,
        filename=filename,
        file_path=rel_path,
        file_type=file_type,
        content_hash=content_hash,
        file_size=len(content),
        status="pending",
    )
    db.add(source)
    await db.flush()
    await db.refresh(source)

    # Log
    db.add(IngestionLog(
        source_id=source.id,
        log_type="ingest",
        action="source_uploaded",
        details=f"File '{filename}' uploaded, size={len(content)} bytes",
    ))

    return source


@router.post("/clip", response_model=SourceResponse, status_code=status.HTTP_201_CREATED)
async def clip_url(
    url: str,
    db: AsyncSession = Depends(get_db),
):
    """Fetch URL content via trafilatura and save as a source.

    The URL content is fetched, extracted as clean text, and stored as a
    ``.url`` type source. Trafilatura is used for content extraction.
    """
    from app.core.config import get_settings
    settings = get_settings()

    if not url.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="Invalid URL")

    try:
        import trafilatura
        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            raise HTTPException(status_code=400, detail="Failed to fetch URL")

        extracted_text = trafilatura.extract(downloaded, include_comments=False)
        if not extracted_text:
            raise HTTPException(status_code=400, detail="No content extracted from URL")
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="trafilatura not installed. Install with: pip install trafilatura",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Content extraction failed: {str(e)}")

    # Build source from extracted content
    content_bytes = extracted_text.encode("utf-8")
    content_hash = _compute_file_hash(content_bytes)
    title = trafilatura.extract_metadata(downloaded)
    title = title.title if title and title.title else url.split("/")[-1] or "Web Clip"

    # Check for duplicate
    existing = await db.execute(
        select(Source).where(Source.content_hash == content_hash)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A source with identical content already exists",
        )

    # Save extracted content only after duplicate validation.
    safe_filename = "".join(c if c.isalnum() or c in "._-" else "_" for c in title)[:100]
    filename = f"{safe_filename}.txt"
    rel_path = _get_storage_path(filename, settings.data_dir)
    abs_path = os.path.join(settings.data_dir, rel_path)

    with open(abs_path, "w", encoding="utf-8") as f:
        f.write(extracted_text)

    source = Source(
        title=title,
        filename=filename,
        file_path=rel_path,
        file_type="url",
        content_hash=content_hash,
        file_size=len(content_bytes),
        content_text=extracted_text,
        source_url=url,
        status="pending",
    )
    db.add(source)
    await db.flush()
    await db.refresh(source)

    # Log
    db.add(IngestionLog(
        source_id=source.id,
        log_type="ingest",
        action="url_clipped",
        details=f"URL '{url}' clipped, extracted {len(extracted_text)} chars",
    ))

    return source


@router.get("", response_model=SourceList)
async def list_sources(
    page: int = 1,
    page_size: int = 20,
    file_type: Optional[str] = None,
    status_filter: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """List all sources with pagination and optional filtering."""
    # Build query
    query = select(Source)
    count_query = select(func.count(Source.id))

    if file_type:
        query = query.where(Source.file_type == file_type)
        count_query = count_query.where(Source.file_type == file_type)

    if status_filter:
        query = query.where(Source.status == status_filter)
        count_query = count_query.where(Source.status == status_filter)

    # Order by most recent
    query = query.order_by(desc(Source.created_at))

    # Pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    # Execute
    result = await db.execute(query)
    sources = result.scalars().all()

    total_result = await db.execute(count_query)
    total = total_result.scalar()

    return SourceList(
        items=list(sources),
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{source_id}", response_model=SourceResponse)
async def get_source(
    source_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get a single source by ID."""
    source = await db.get(Source, source_id)
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")
    return source


@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_source(
    source_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete a source and all associated data (wiki pages, analyses).

    This removes the database records. The original file in the sources
    directory is kept as an immutable archive.
    """
    source = await db.get(Source, source_id)
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")

    # Delete associated wiki pages (cascade via foreign key or manual)
    await db.execute(
        select(WikiPage).where(WikiPage.source_id == source_id)
    )

    # Delete associated munger analyses
    from sqlalchemy import delete
    await db.execute(
        delete(MungerAnalysis).where(MungerAnalysis.source_id == source_id)
    )

    # Delete associated wiki pages
    await db.execute(
        delete(WikiPage).where(WikiPage.source_id == source_id)
    )

    # Delete associated ingestion logs
    await db.execute(
        delete(IngestionLog).where(IngestionLog.source_id == source_id)
    )

    # Delete ingest timeline and queue rows
    await db.execute(
        delete(IngestEvent).where(IngestEvent.source_id == source_id)
    )
    await db.execute(
        delete(IngestJob).where(IngestJob.source_id == source_id)
    )

    # Delete source
    await db.delete(source)

    # Log
    db.add(IngestionLog(
        log_type="ingest",
        action="source_deleted",
        details=f"Source {source_id} deleted",
    ))

    return None


ALLOWED_INGEST_SKILLS = frozenset(
    {"ingest", "default-ingest", "entity-extract-only", "wiki-regenerate", "munger-12-dimension"}
)


@router.post("/{source_id}/ingest", status_code=status.HTTP_202_ACCEPTED)
async def trigger_ingest(
    source_id: int,
    skill: str = Query(default="ingest", description="DeerFlow skill name for this job"),
    db: AsyncSession = Depends(get_db),
):
    """Enqueue ingestion for a source. Worker process executes the job."""
    source = await db.get(Source, source_id)
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")

    skill_name = skill if skill in ALLOWED_INGEST_SKILLS else "ingest"
    source.status = "pending"
    source.error_message = None
    job = await enqueue_ingest_job(db, source_id, skill_name=skill_name)

    db.add(IngestionLog(
        source_id=source_id,
        log_type="ingest",
        action="ingest_triggered",
        details=f"Ingest job {job.id} enqueued for source {source_id} (skill={skill_name})",
    ))

    return {
        "message": "Ingestion triggered",
        "source_id": source_id,
        "job_id": job.id,
        "skill_name": skill_name,
    }


@router.post("/{source_id}/backfill", status_code=status.HTTP_202_ACCEPTED)
async def backfill_source(
    source_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Re-run provenance pipeline on existing source content (no re-upload)."""
    from sqlalchemy import delete

    source = await db.get(Source, source_id)
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")
    if not source.content_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Source has no extracted text; run full ingest first",
        )

    await db.execute(delete(ChunkExtraction).where(ChunkExtraction.source_id == source_id))
    await db.execute(delete(Chunk).where(Chunk.source_id == source_id))
    await db.execute(delete(EntityMention).where(EntityMention.source_id == source_id))
    await db.execute(delete(EntityRelationship).where(EntityRelationship.source_id == source_id))

    source.status = "pending"
    source.error_message = None
    job = await enqueue_ingest_job(db, source_id, skill_name="ingest")

    db.add(IngestionLog(
        source_id=source_id,
        log_type="ingest",
        action="backfill_triggered",
        details=f"Backfill job {job.id} enqueued for source {source_id}",
    ))

    return {
        "message": "Backfill triggered",
        "source_id": source_id,
        "job_id": job.id,
        "skill_name": "ingest",
    }


@router.get("/{source_id}/status")
async def get_ingest_status(
    source_id: int,
    since_id: int | None = Query(default=None, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """Get ingestion status, recent logs, and timeline events for a source."""
    source = await db.get(Source, source_id)
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")

    result = await db.execute(
        select(IngestionLog)
        .where(IngestionLog.source_id == source_id)
        .order_by(desc(IngestionLog.created_at))
        .limit(10)
    )
    logs = result.scalars().all()

    active_job = await get_active_job(db, source_id)
    latest_job_result = await db.execute(
        select(IngestJob)
        .where(IngestJob.source_id == source_id)
        .order_by(desc(IngestJob.id))
        .limit(1)
    )
    latest_job = latest_job_result.scalar_one_or_none()

    events_query = select(IngestEvent).where(IngestEvent.source_id == source_id).order_by(IngestEvent.id.asc())
    if since_id is not None:
        events_query = events_query.where(IngestEvent.id > since_id)
    events_query = events_query.limit(limit + 1)
    events_result = await db.execute(events_query)
    event_rows = list(events_result.scalars().all())
    events_has_more = len(event_rows) > limit
    if events_has_more:
        event_rows = event_rows[:limit]

    current_step = None
    step_metrics: dict = {}
    for event in reversed(event_rows):
        if event.event_type == "pipeline_step_start" and current_step is None:
            payload = event.payload or {}
            current_step = {
                "key": payload.get("step_key"),
                "label": payload.get("label"),
                "index": payload.get("step_index"),
                "total": payload.get("step_total"),
            }
        if event.event_type == "pipeline_step_complete":
            payload = event.payload or {}
            if payload.get("metrics"):
                step_metrics.update(payload["metrics"])
            if current_step is None:
                current_step = {
                    "key": payload.get("step_key"),
                    "label": payload.get("label"),
                    "index": payload.get("step_index"),
                    "total": payload.get("step_total"),
                }
            break

    # Live substage progress (cheap COUNT aggregates) so the UI can show per-task
    # dispatched/done/failed instead of only step-level done/not-done.
    from app.services.chunk_map_status import count_chunks_by_status

    map_progress = await count_chunks_by_status(source_id)

    total_entities = (
        await db.execute(
            select(func.count(func.distinct(EntityMention.entity_id))).where(
                EntityMention.source_id == source_id
            )
        )
    ).scalar() or 0
    wiki_pages_done = (
        await db.execute(
            select(func.count(func.distinct(EntityMention.entity_id)))
            .select_from(EntityMention)
            .join(Entity, Entity.id == EntityMention.entity_id)
            .where(
                EntityMention.source_id == source_id,
                Entity.wiki_page_id.is_not(None),
            )
        )
    ).scalar() or 0
    wiki_progress = {"pages_done": wiki_pages_done, "total": total_entities}

    return {
        "source_id": source_id,
        "status": source.status,
        "error_message": source.error_message,
        "updated_at": source.updated_at,
        "job_id": (active_job or latest_job).id if (active_job or latest_job) else None,
        "map_progress": map_progress,
        "wiki_progress": wiki_progress,
        "recent_logs": [
            {
                "id": log.id,
                "action": log.action,
                "log_type": log.log_type,
                "created_at": log.created_at,
            }
            for log in logs
        ],
        "events": [
            {
                "id": event.id,
                "event_type": event.event_type,
                "payload": event.payload,
                "created_at": event.created_at,
                "job_id": event.job_id,
            }
            for event in event_rows
        ],
        "events_has_more": events_has_more,
        "current_step": current_step,
        "step_metrics": step_metrics,
    }
