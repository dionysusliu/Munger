# Context Snapshot (refinement): Backend Concurrency Architecture

**Created:** 2026-06-08T17:00:00Z  
**Parent spec:** `.omx/specs/deep-interview-ingest-realtime-progress.md`

## Refinement topic
User wants multiple ingest jobs (and future workflows) to run in parallel, bounded by backend capacity. Uncertain whether FastAPI event loop currently serializes work.

## Current execution model (evidence)

| Layer | What happens |
|-------|----------------|
| **Server** | Single uvicorn process, single worker (`Dockerfile`: `uvicorn ... --reload`, no `--workers`) |
| **Trigger** | `POST /sources/{id}/ingest` → `BackgroundTasks.add_task(_run_ingestion_pipeline)` |
| **Pipeline** | `async def _run_ingestion_pipeline` → `await IngestRunner.run()` → `await agent.ainvoke()` |
| **LLM** | `await httpx` in `MungerLLMChatModel._agenerate` — non-blocking I/O |
| **PDF** | `asyncio.to_thread()` in `storage_service._extract_pdf` — off event loop |
| **Upload** | Does NOT auto-start ingest; returns `pending` source only |

## Serial vs parallel today

**Not strictly serial across requests.** Multiple ingest triggers from separate HTTP requests each add a BackgroundTask; all run on the **same asyncio event loop** and interleave at `await` points. So 3 ingests can make progress concurrently while waiting on LLM HTTP responses.

**Effectively serial when:**
- Any step runs **sync CPU work** on the event loop (blocks all API + all ingests)
- SQLite write lock contention under concurrent DB commits
- LiteParse/OCR/thread pool exhaustion

**BackgroundTasks limitations:**
- Not a durable job queue (lost on restart)
- No concurrency cap (unbounded parallel ingests possible)
- No backpressure / priority
- Not suitable for long-running multi-workflow fleet at scale

## Future needs (user stated)
- Multiple files ingested in parallel
- More workflow types later
- Parallelism up to infra capacity

## Open architecture choices
- In-process asyncio pool with semaphore vs dedicated worker process(es)
- Durable queue (Redis/Postgres/SQLite queue) vs fire-and-forget BackgroundTasks
- SQLite single-writer limits vs migrate job state DB
- DeerFlow-style RunManager + Worker separation
