# SP0.1 — Characterization & Infra-Readiness Test Suite Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax. These are **characterization tests of EXISTING behavior** — the loop is: write test asserting current outcome → run → if it PASSES, behavior is locked as the parity baseline; if it FAILS, decide whether the expectation is wrong (fix the test) or a real bug was found (flag it, do not silently "fix" by weakening the assertion).

**Goal:** Lock down the current LangGraph ingest pipeline with a thorough test suite — infra readiness + per-step desired outcomes + full E2E + job-queue lifecycle — so the SP1 DBOS migration can prove parity and the BIG TABLE harness (SP0) has its first installment.

**Architecture:** Three layers. (1) `tests/infra/` — live-DB readiness checks. (2) `tests/integration/test_ingest_graph_e2e.py` — run the real compiled graph on a tiny scripted-LLM fixture against `munger_test`, then assert each step's DB outcome. (3) `tests/integration/test_job_queue_lifecycle.py` — exercise the DB-backed queue. Steps cannot be invoked in isolation (they require the compiled graph), so per-step characterization is done by asserting cumulative DB state after one full graph run, plus direct service-level tests where a service entry point exists.

**Tech Stack:** pytest, SQLAlchemy async (psycopg), Postgres + pgvector, `tests/fixtures/fake_llm.py::ScriptedLLMService`.

**Prerequisite:** `munger_test` Postgres reachable; `TEST_DATABASE_URL` exported; backend deps installed. Task 0 establishes this.

**Key references (from investigation):**
- Steps: `app/runtime/graphs/nodes/nodes_intake.py`, `nodes_cognify.py`; order in `app/runtime/pipeline_events.py::GRAPH_STEP_ORDER` (11 steps).
- Graph build: `app/runtime/graphs/ingest.py::build_ingest_graph(services, checkpointer)`; run via `await graph.ainvoke({"source_id": id, "job_id": None}, config={"configurable": {"thread_id": "..."}})`.
- Services: `ChunkService.ensure_chunks(source_id)`, `ResolutionService.reduce_entities(source_id)`, `LinkingService.link_source(source_id)`, `WikiService.create_page(...)`.
- `RuntimeServices` construction: `app/runtime/context.py` (see Task 2 Step 1 — read it for the exact constructor before writing fixtures).
- Models: `app/models/` (Source, Chunk, ChunkExtraction, Entity, EntityMention, EntityRelationship, WikiPage, WikiLink, IngestJob, IngestEvent).
- Job queue: `app/services/ingest_job_service.py` (enqueue_ingest_job, claim_pending_jobs, mark_job_running, touch_job_heartbeat, complete_job, reconcile_stale_jobs).

---

## File Structure

| File | Responsibility | Action |
|------|----------------|--------|
| `munger/backend/tests/infra/__init__.py` | package marker | Create |
| `munger/backend/tests/infra/test_db_readiness.py` | connection, pgvector, migrations-at-head, tables exist, embedding dim | Create |
| `munger/backend/tests/fixtures/ingest_fixtures.py` | build RuntimeServices with ScriptedLLMService + a 2-chunk scripted source | Create |
| `munger/backend/tests/integration/test_ingest_graph_e2e.py` | full graph run + per-step DB outcome assertions | Create |
| `munger/backend/tests/integration/test_intake_steps.py` | register/parse/hash_dedup characterization | Create |
| `munger/backend/tests/integration/test_service_steps.py` | chunk/link/wiki service-level characterization | Create |
| `munger/backend/tests/integration/test_job_queue_lifecycle.py` | enqueue/claim/heartbeat/complete/reconcile | Create (replaces placeholder `test_postgres_worker.py`) |

---

## Task 0: Environment baseline (green before writing anything)

**Files:** none

- [ ] **Step 1: Install backend deps**

Run: `cd munger/backend && pip install -r requirements.txt`
Expected: completes without error.

- [ ] **Step 2: Ensure the test database exists**

Run: `cd munger/backend && python scripts/bootstrap_test_postgres.py`
Expected: `munger_test` DB exists with pgvector; idempotent if already created. (If the script needs admin creds, set `MUNGER_POSTGRES_ADMIN_URL`.)

- [ ] **Step 3: Run the existing suite to confirm a clean baseline**

Run: `cd munger/backend && TEST_DATABASE_URL=postgresql+psycopg://munger_app:Munger.App.2026@localhost:5432/munger_test pytest tests/ -q`
Expected: existing tests pass (or record exact pre-existing failures — do NOT proceed to write new tests on top of unexplained red; report first).

- [ ] **Step 4: No commit** (verification only). Record baseline pass/fail counts in the task report.

---

## Task 1: Infra-readiness tests

**Files:**
- Create: `munger/backend/tests/infra/__init__.py` (empty)
- Create: `munger/backend/tests/infra/test_db_readiness.py`

- [ ] **Step 1: Write the tests**

Create `munger/backend/tests/infra/test_db_readiness.py`:

```python
"""Data-infra readiness: the suite must fail loudly if Postgres/pgvector/migrations aren't ready."""

from sqlalchemy import text

from app.core.config import get_settings
from app.core.database import Base, async_session_maker, engine
from tests.conftest import run_async

EXPECTED_TABLES = {
    "sources", "chunks", "chunk_extractions", "entities", "entity_mentions",
    "entity_relationships", "wiki_pages", "wiki_links", "ingest_jobs",
    "ingest_events", "configs",
}


def test_database_connection_works():
    async def _inner():
        async with async_session_maker() as session:
            return (await session.execute(text("SELECT 1"))).scalar()
    assert run_async(_inner()) == 1


def test_pgvector_extension_installed():
    async def _inner():
        async with async_session_maker() as session:
            return (await session.execute(
                text("SELECT count(*) FROM pg_extension WHERE extname = 'vector'")
            )).scalar()
    assert run_async(_inner()) == 1, "pgvector extension missing — run scripts/bootstrap_test_postgres.py"


def test_expected_tables_exist():
    async def _inner():
        async with engine.begin() as conn:
            rows = (await conn.execute(text(
                "SELECT table_name FROM information_schema.tables WHERE table_schema='public'"
            ))).scalars().all()
        return set(rows)
    present = run_async(_inner())
    missing = EXPECTED_TABLES - present
    assert not missing, f"missing tables (migrations not at head?): {missing}"


def test_embedding_dimension_matches_settings():
    settings = get_settings()
    assert settings.embedding_dimensions == 768

    async def _inner():
        async with async_session_maker() as session:
            return (await session.execute(text(
                "SELECT a.atttypmod FROM pg_attribute a "
                "JOIN pg_class c ON c.oid = a.attrelid "
                "WHERE c.relname='chunks' AND a.attname='embedding'"
            ))).scalar()
    # pgvector stores dimension in atttypmod for vector columns
    dim = run_async(_inner())
    assert dim == settings.embedding_dimensions, f"chunks.embedding dim {dim} != {settings.embedding_dimensions}"
```

- [ ] **Step 2: Run the tests**

Run: `cd munger/backend && pytest tests/infra/test_db_readiness.py -v`
Expected: PASS (4 tests). If `test_embedding_dimension_matches_settings` fails on `atttypmod`, read how pgvector exposes the dimension in this version and adjust the query — the *intent* (chunks.embedding is 768-dim) is the assertion.

- [ ] **Step 3: Commit**

```bash
git add munger/backend/tests/infra/
git commit -m "test(infra): add data-infra readiness checks (connection, pgvector, tables, dim)"
```

---

## Task 2: Scripted ingest fixture (RuntimeServices + a 2-chunk source)

**Files:**
- Create: `munger/backend/tests/fixtures/ingest_fixtures.py`

- [ ] **Step 1: Read the exact constructors before writing the fixture**

Read these to get exact signatures (do not guess):
- `app/runtime/context.py` — `RuntimeServices` fields / `from_settings`.
- `app/services/chunk_service.py`, `map_chunk_service.py`, `resolution_service.py`, `linking_service.py`, `wiki_service.py`, `entity_service.py` — constructor args.

- [ ] **Step 2: Write the fixture builder**

Create `munger/backend/tests/fixtures/ingest_fixtures.py`. Use the real constructors found in Step 1; the shape below matches the investigation — adjust arg names to the real signatures:

```python
"""Builds a RuntimeServices wired to ScriptedLLMService for deterministic graph runs."""

from __future__ import annotations

from app.core.config import Settings
from app.runtime.context import RuntimeServices
from app.services.chunk_service import ChunkService
from app.services.map_chunk_service import MapChunkService
from app.services.resolution_service import ResolutionService
from app.services.linking_service import LinkingService
from app.services.wiki_service import WikiService
from app.services.entity_service import EntityService
from app.services.storage_service import StorageService
from tests.fixtures.fake_llm import ScriptedLLMService


def scripted_services(scripts: list[dict], settings: Settings | None = None) -> RuntimeServices:
    """RuntimeServices with a scripted LLM. `settings` defaults to service map mode."""
    settings = settings or Settings(ingest_orchestrator="graph", ingest_map_mode="service")
    llm = ScriptedLLMService(scripts=scripts)
    return RuntimeServices(
        settings=settings,
        storage=StorageService(settings),
        llm=llm,
        entity=EntityService(llm=llm),
        chunk=ChunkService(llm=llm, settings=settings),
        map_chunks=MapChunkService(llm=llm, settings=settings),
        resolution=ResolutionService(llm=llm, settings=settings),
        linking=LinkingService(llm=llm, settings=settings),
        wiki=WikiService(),
    )


def two_entity_scripts() -> list[dict]:
    """Round-0 extraction for a single-chunk source naming two entities + one relationship."""
    return [
        {
            "entities": [
                {"name": "Charlie Munger", "type": "person", "description": "Investor", "char_start": 0, "char_end": 14},
                {"name": "Mental Models", "type": "concept", "description": "Latticework of models", "char_start": 20, "char_end": 33},
            ],
            "relationships": [
                {"source": "Charlie Munger", "target": "Mental Models", "type": "advocates", "description": "promotes"},
            ],
        },
    ]
```

- [ ] **Step 3: Smoke-check the import**

Run: `cd munger/backend && python -c "from tests.fixtures.ingest_fixtures import scripted_services, two_entity_scripts; print('ok')"`
Expected: prints `ok`. If a constructor arg is wrong, fix it against the real signature from Step 1.

- [ ] **Step 4: Commit**

```bash
git add munger/backend/tests/fixtures/ingest_fixtures.py
git commit -m "test(fixtures): scripted RuntimeServices builder for deterministic graph runs"
```

---

## Task 3: Full E2E graph run + per-step DB outcome assertions

**Files:**
- Create: `munger/backend/tests/integration/test_ingest_graph_e2e.py`

This is the central characterization test (the parity oracle). One full graph run, then assert the cumulative outcome of every step.

- [ ] **Step 1: Write the E2E test**

Create `munger/backend/tests/integration/test_ingest_graph_e2e.py`:

```python
"""End-to-end characterization: run the real compiled graph with a scripted LLM, assert each step's outcome.

This is the SP1 parity oracle. If the DBOS spine (SP1) is at parity, the same assertions must hold.
"""

from sqlalchemy import func, select

from app.core.database import async_session_maker
from app.models.source import Source
from app.models.chunk import Chunk
from app.models.entity import Entity, EntityMention
from app.models.wiki import WikiPage
from app.runtime.graphs.ingest import build_ingest_graph
from tests.conftest import run_async
from tests.fixtures.ingest_fixtures import scripted_services, two_entity_scripts


def _run_graph(source_id: int):
    services = scripted_services(two_entity_scripts())
    graph = build_ingest_graph(services, checkpointer=None)

    async def _inner():
        return await graph.ainvoke(
            {"source_id": source_id, "job_id": None},
            config={"configurable": {"thread_id": f"test-{source_id}"}},
        )
    return run_async(_inner())


def test_full_ingest_reaches_completed_and_populates_graph(create_source):
    source = create_source(
        status="pending",
        content_text="Charlie Munger champions Mental Models as a latticework for decisions.",
    )
    _run_graph(source.id)

    async def _counts():
        async with async_session_maker() as session:
            src = await session.get(Source, source.id)
            chunks = (await session.execute(
                select(func.count()).select_from(Chunk).where(Chunk.source_id == source.id)
            )).scalar()
            entities = (await session.execute(select(func.count()).select_from(Entity))).scalar()
            mentions = (await session.execute(
                select(func.count()).select_from(EntityMention).where(EntityMention.source_id == source.id)
            )).scalar()
            pages = (await session.execute(
                select(func.count()).select_from(WikiPage).where(WikiPage.source_id == source.id)
            )).scalar()
            embedded = (await session.execute(
                select(func.count()).select_from(Chunk).where(
                    Chunk.source_id == source.id, Chunk.embedding.isnot(None)
                )
            )).scalar()
            return src.status, chunks, entities, mentions, pages, embedded

    status, chunks, entities, mentions, pages, embedded = run_async(_counts())
    assert status == "completed", "finalize_ingest must set source.status=completed"
    assert chunks >= 1, "chunk_document must create chunk rows"
    assert embedded == chunks, "map_chunks must embed every chunk"
    assert entities >= 2, "reduce_entities must create the scripted entities"
    assert mentions >= 2, "reduce_entities must create entity_mentions"
    assert pages >= 3, "generate_wiki_pages must create a summary page + one per entity"
```

- [ ] **Step 2: Run it**

Run: `cd munger/backend && pytest tests/integration/test_ingest_graph_e2e.py -v`
Expected: PASS. If it fails, read the failing step's node in `nodes_cognify.py`/`nodes_intake.py` and the scripted-LLM call sequence; adjust the script (e.g. add glean-round entries) or the assertion to match real current behavior. A genuine bug → flag it, don't weaken the assertion.

- [ ] **Step 3: Commit**

```bash
git add munger/backend/tests/integration/test_ingest_graph_e2e.py
git commit -m "test(ingest): E2E graph characterization with scripted LLM (parity oracle)"
```

---

## Task 4: Intake-step characterization (register / parse / hash_dedup)

**Files:**
- Create: `munger/backend/tests/integration/test_intake_steps.py`

- [ ] **Step 1: Read the intake nodes**

Read `app/runtime/graphs/nodes/nodes_intake.py` (n_register, n_parse, n_hash_dedup) and `app/runtime/graphs/intake.py` (build_intake_subgraph) for exact invocation.

- [ ] **Step 2: Write the tests**

Create `munger/backend/tests/integration/test_intake_steps.py`:

```python
"""Characterize the intake subgraph: register_source, parse_document, hash_dedup."""

from app.core.database import async_session_maker
from app.models.source import Source
from app.runtime.graphs.intake import build_intake_subgraph
from tests.conftest import run_async
from tests.fixtures.ingest_fixtures import scripted_services, two_entity_scripts


def _run_intake(source_id: int):
    services = scripted_services(two_entity_scripts())
    sub = build_intake_subgraph(services)

    async def _inner():
        return await sub.ainvoke(
            {"source_id": source_id, "job_id": None},
            config={"configurable": {"thread_id": f"intake-{source_id}"}},
        )
    return run_async(_inner())


def test_register_sets_status_extracting_then_parse_caches_text(create_source):
    source = create_source(status="pending", content_text="Some content for parsing.")
    state = _run_intake(source.id)

    async def _src():
        async with async_session_maker() as session:
            return await session.get(Source, source.id)
    src = run_async(_src())
    assert src.content_text and len(src.content_text) > 0, "parse_document must populate content_text"
    assert state.get("is_duplicate") is False


def test_hash_dedup_flags_second_identical_source(create_source):
    first = create_source(
        title="Original", status="completed",
        content_text="Identical body for dedup test.",
    )
    # create a second pending source with the SAME content_hash the pipeline computes
    second = create_source(
        title="Duplicate", status="pending",
        content_text="Identical body for dedup test.",
    )
    state = _run_intake(second.id)
    # hash_dedup compares content_hash of completed sources; identical text → duplicate
    assert state.get("is_duplicate") is True, "hash_dedup must flag the identical second source"
    assert state.get("duplicate_of_source_id") == first.id
```

Note: `create_source` in conftest sets `content_hash=f"hash-{title...}"`, so the two sources above get DIFFERENT hashes. Read how the pipeline computes `content_hash` (parse step) — if dedup keys off the pipeline-computed hash rather than the fixture's, set both sources' `content_text` identical AND let parse recompute, or set matching `content_hash` explicitly via a direct DB update in the test. Adjust the test to the real dedup key discovered in Step 1.

- [ ] **Step 3: Run + iterate**

Run: `cd munger/backend && pytest tests/integration/test_intake_steps.py -v`
Expected: PASS after aligning the dedup key with real behavior (Step 1).

- [ ] **Step 4: Commit**

```bash
git add munger/backend/tests/integration/test_intake_steps.py
git commit -m "test(ingest): characterize intake steps (register, parse, hash_dedup)"
```

---

## Task 5: Service-level characterization (chunk / link / wiki)

**Files:**
- Create: `munger/backend/tests/integration/test_service_steps.py`

Covers the weak/untested steps that have direct service entry points: `chunk_document` (ChunkService.ensure_chunks), `link_entities` (LinkingService.link_source), `generate_wiki_pages` + `link_wiki_pages` (WikiService).

- [ ] **Step 1: Read the service signatures**

Read `app/services/chunk_service.py::ensure_chunks`, `app/services/linking_service.py::link_source`, `app/services/wiki_service.py::create_page` (+ the WikiPageCreate schema in `app/schemas/`). Confirm return shapes.

- [ ] **Step 2: Write `ensure_chunks` characterization**

Create `munger/backend/tests/integration/test_service_steps.py`:

```python
"""Service-level characterization for chunk/link/wiki steps."""

from sqlalchemy import func, select

from app.core.config import Settings
from app.core.database import async_session_maker
from app.models.chunk import Chunk
from app.services.chunk_service import ChunkService
from tests.conftest import run_async
from tests.fixtures.fake_llm import ScriptedLLMService


def test_ensure_chunks_creates_chunk_rows(create_source):
    source = create_source(
        status="pending",
        content_text=("Sentence one. " * 200),  # enough tokens to force >=1 chunk
    )
    settings = Settings(ingest_orchestrator="graph")
    svc = ChunkService(llm=ScriptedLLMService(), settings=settings)

    async def _inner():
        await svc.ensure_chunks(source.id)
        async with async_session_maker() as session:
            rows = (await session.execute(
                select(Chunk).where(Chunk.source_id == source.id)
            )).scalars().all()
            return rows
    rows = run_async(_inner())
    assert len(rows) >= 1
    for c in rows:
        assert c.content and c.token_count and c.token_count > 0
        assert c.map_status == "pending"
```

- [ ] **Step 3: Run it**

Run: `cd munger/backend && pytest tests/integration/test_service_steps.py::test_ensure_chunks_creates_chunk_rows -v`
Expected: PASS (adjust constructor args / `map_status` constant to the real ones from Step 1 if needed).

- [ ] **Step 4: Add link + wiki characterization to the same file**

Append tests that: (a) after a full reduce, `LinkingService.link_source(source_id)` populates `entities.embedding` and adds cross-chunk `entity_relationships`; (b) `WikiService.create_page(...)` creates a `wiki_pages` row with a unique slug, and a second create with the same title produces a distinct slug. Build on the real signatures from Step 1. Run each: `pytest tests/integration/test_service_steps.py -v` → PASS.

- [ ] **Step 5: Commit**

```bash
git add munger/backend/tests/integration/test_service_steps.py
git commit -m "test(ingest): service-level characterization (chunk/link/wiki)"
```

---

## Task 6: Job-queue lifecycle

**Files:**
- Create: `munger/backend/tests/integration/test_job_queue_lifecycle.py`
- Delete: `munger/backend/tests/integration/test_postgres_worker.py` (empty placeholder)

- [ ] **Step 1: Read the job service**

Read `app/services/ingest_job_service.py` for exact signatures of enqueue_ingest_job, claim_pending_jobs, mark_job_running, touch_job_heartbeat, complete_job, reconcile_stale_jobs, and the `IngestJob` model fields.

- [ ] **Step 2: Write the lifecycle tests**

Create `munger/backend/tests/integration/test_job_queue_lifecycle.py`:

```python
"""DB-backed ingest job queue lifecycle characterization."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import update

from app.core.config import get_settings
from app.core.database import async_session_maker
from app.models.ingest_job import IngestJob
from app.services.ingest_job_service import (
    enqueue_ingest_job, claim_pending_jobs, mark_job_running,
    touch_job_heartbeat, complete_job, reconcile_stale_jobs,
)
from tests.conftest import run_async


def test_enqueue_is_idempotent_per_source(create_source):
    source = create_source(status="pending")

    async def _inner():
        async with async_session_maker() as session:
            j1 = await enqueue_ingest_job(session, source.id)
            await session.commit()
        async with async_session_maker() as session:
            j2 = await enqueue_ingest_job(session, source.id)
            await session.commit()
        return j1.id, j2.id
    a, b = run_async(_inner())
    assert a == b, "a second enqueue for an active source must return the same job"


def test_claim_then_run_then_complete(create_source):
    source = create_source(status="pending")
    settings = get_settings()

    async def _inner():
        async with async_session_maker() as session:
            job = await enqueue_ingest_job(session, source.id)
            await session.commit()
            jid = job.id
        async with async_session_maker() as session:
            claimed = await claim_pending_jobs(session, worker_id="w1", limit=5)
            await session.commit()
        async with async_session_maker() as session:
            await mark_job_running(session, jid, "thread-1")
            await touch_job_heartbeat(session, jid)
            await complete_job(session, jid, failed=False, error=None)
            await session.commit()
        async with async_session_maker() as session:
            final = await session.get(IngestJob, jid)
            return [c.id for c in claimed], final.status
    claimed_ids, status = run_async(_inner())
    assert claimed_ids and claimed_ids[0] is not None
    assert status == "completed"


def test_reconcile_requeues_stale_running_job(create_source):
    source = create_source(status="pending")
    settings = get_settings()

    async def _inner():
        async with async_session_maker() as session:
            job = await enqueue_ingest_job(session, source.id)
            await session.commit()
            jid = job.id
        async with async_session_maker() as session:
            await mark_job_running(session, jid, "thread-stale")
            stale_ts = datetime.now(timezone.utc) - timedelta(minutes=settings.job_stale_minutes + 5)
            await session.execute(
                update(IngestJob).where(IngestJob.id == jid).values(heartbeat_at=stale_ts)
            )
            await session.commit()
        async with async_session_maker() as session:
            n = await reconcile_stale_jobs(session, settings)
            await session.commit()
        async with async_session_maker() as session:
            return n, (await session.get(IngestJob, jid)).status
    requeued, status = run_async(_inner())
    assert requeued >= 1
    assert status == "pending", "stale running job must be requeued to pending"
```

- [ ] **Step 3: Remove the placeholder and run**

```bash
git rm munger/backend/tests/integration/test_postgres_worker.py
cd munger/backend && pytest tests/integration/test_job_queue_lifecycle.py -v
```
Expected: PASS (3 tests). Adjust to real signatures from Step 1 (e.g. `enqueue_ingest_job` return type, datetime tz handling).

- [ ] **Step 4: Commit**

```bash
git add munger/backend/tests/integration/test_job_queue_lifecycle.py
git commit -m "test(queue): characterize job lifecycle (enqueue/claim/complete/reconcile)"
```

---

## Task 7: Full suite green + tag the parity baseline

**Files:** none

- [ ] **Step 1: Run the entire suite**

Run: `cd munger/backend && pytest tests/ -q`
Expected: all green (new + existing). Record counts.

- [ ] **Step 2: Document the baseline in the suite report**

In the task report, list which of the 11 GRAPH_STEP_ORDER steps now have an explicit outcome assertion and where. Confirm every step is covered by at least one of: E2E (Task 3), intake (Task 4), service-level (Task 5), or pre-existing (map_chunks, reduce_entities).

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "test: SP0.1 characterization + infra suite complete (parity baseline)" --allow-empty
```

---

## Self-Review

**Spec coverage (against spec §9 BIG TABLE + §11 SP0/SP1):** This is SP0's first installment — the characterization layer of the BIG TABLE (constraint/outcome checks) plus the infra-readiness layer, scoped to the *current* architecture. It is the parity oracle SP1.1 depends on. Eval-harness (Ragas/DeepEval) and alerting are later SP0 installments, not in this plan.

**Step coverage:** register_source, parse_document, hash_dedup → Task 4; chunk_document, link_entities, generate_wiki_pages, link_wiki_pages → Tasks 3+5; summarize_source, finalize_ingest, map_chunks, reduce_entities → Task 3 (+ pre-existing for the last two). Infra → Task 1. Queue → Task 6.

**Placeholder scan:** Tasks include explicit "read the real signature" steps before fixture/service code because exact constructor args were not all verified during planning — these are concrete read actions, not deferred work. Test bodies are complete and runnable; where current behavior may differ (dedup key, pgvector dim introspection, glean-round script count), the step says exactly what to read and how to align, with the *intent* assertion fixed.

**Consistency:** `scripted_services` / `two_entity_scripts` (Task 2) are used in Tasks 3–5. `run_async` imported from `tests.conftest` throughout. Model imports (`app.models.*`) match the investigation's table map. Job-service function names match `ingest_job_service.py`.

**Characterization caveat (important for executors):** these tests assert CURRENT behavior. A failing test means either the expectation is mis-stated (align it to real behavior after reading the code) OR a genuine bug exists (flag it in the task report — do not silently weaken the assertion to force green).
