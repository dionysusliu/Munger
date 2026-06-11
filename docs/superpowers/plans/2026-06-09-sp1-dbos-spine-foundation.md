# SP1.1 — DBOS Spine Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a durable DBOS-backed ingest orchestrator path behind the existing `INGEST_ORCHESTRATOR` flag, strangler-wrapping the current LangGraph pipeline without changing its behavior.

**Architecture:** DBOS Transact (MIT library, Postgres-backed durable execution) runs *inside* the existing worker process. A synchronous DBOS workflow wraps one step that executes the current async ingest pipeline via `asyncio.run` (safe — DBOS runs steps in their own threads). The workflow forces the `graph` path internally, so `INGEST_ORCHESTRATOR=dbos` gains durability/observability while reusing all existing pipeline logic. When the flag is `graph`/`agent` (default), nothing changes. DBOS stores its state in a `dbos` schema inside the same Postgres database — no new database, no new server.

**Tech Stack:** Python 3, FastAPI, SQLAlchemy (async, psycopg), DBOS Transact, Postgres (Pigsty + pgvector), pytest.

**Prerequisite:** Tests require the `munger_test` Postgres database (per `munger/backend/tests/conftest.py`). If not yet created: `python munger/backend/scripts/bootstrap_test_postgres.py`. Run all commands from `munger/backend/` with `TEST_DATABASE_URL` exported.

---

## File Structure

| File | Responsibility | Action |
|------|----------------|--------|
| `munger/backend/requirements.txt` | dependency manifest | Modify — add `dbos` |
| `munger/backend/app/core/config.py` | settings | Modify — add DBOS system-db config + validate orchestrator value |
| `munger/backend/app/runtime/dbos_app.py` | DBOS singleton: configure / launch / destroy | Create |
| `munger/backend/app/runtime/dbos_ingest.py` | durable `ingest_source_workflow` + step bridging to async pipeline | Create |
| `munger/backend/app/runtime/ingest_runner.py` | route `dbos` orchestrator → workflow; add `orchestrator` override to prevent recursion | Modify |
| `munger/backend/app/worker/runner.py` | launch DBOS once at worker startup | Modify |
| `munger/backend/tests/unit/test_config_orchestrator.py` | config validation tests | Create |
| `munger/backend/tests/integration/test_dbos_ingest.py` | DBOS init + workflow routing/durability tests | Create |

---

## Task 1: Add the DBOS dependency and verify the sync-workflow + asyncio bridge

**Files:**
- Modify: `munger/backend/requirements.txt`

- [ ] **Step 1: Add the dependency**

Append to `munger/backend/requirements.txt`:

```
dbos>=1.0.0
```

- [ ] **Step 2: Install it**

Run: `cd munger/backend && pip install -r requirements.txt`
Expected: `dbos` and its transitive deps install without conflict.

- [ ] **Step 3: Verify import + the exact runtime pattern this plan relies on**

This spike confirms (a) DBOS imports, (b) a **synchronous** workflow whose step calls `asyncio.run(...)` works against the test Postgres using a `dbos` schema in the same database. Create a throwaway file `munger/backend/_spike_dbos.py`:

```python
import asyncio
import os
from dbos import DBOS, DBOSConfig

sync_url = os.environ["TEST_DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://", 1)
DBOS(config=DBOSConfig(name="munger", system_database_url=sync_url, dbos_system_schema="dbos"))

@DBOS.step()
def _step(x: int) -> int:
    async def _inner() -> int:
        await asyncio.sleep(0)
        return x * 2
    return asyncio.run(_inner())

@DBOS.workflow()
def _wf(x: int) -> int:
    return _step(x)

DBOS.launch()
print("RESULT", _wf(21))
DBOS.destroy()
```

Run: `cd munger/backend && TEST_DATABASE_URL=$TEST_DATABASE_URL python _spike_dbos.py`
Expected: prints `RESULT 42`, no exception. Confirms the sync-workflow + `asyncio.run`-in-step pattern and the `dbos` schema creation.

- [ ] **Step 4: Delete the spike and commit**

```bash
rm munger/backend/_spike_dbos.py
git add munger/backend/requirements.txt
git commit -m "build: add DBOS Transact dependency"
```

---

## Task 2: Add DBOS system-database config (same Postgres, `dbos` schema)

**Files:**
- Modify: `munger/backend/app/core/config.py`
- Test: `munger/backend/tests/unit/test_config_orchestrator.py`

- [ ] **Step 1: Write the failing test**

Create `munger/backend/tests/unit/test_config_orchestrator.py`:

```python
from app.core.config import Settings


def test_dbos_system_database_url_derived_from_database_url():
    s = Settings(DATABASE_URL="postgresql+psycopg://u:p@host:5432/munger_test")
    # libpq (sync) form of the SAME database — DBOS stores its state in a schema
    assert s.dbos_system_database_url == "postgresql://u:p@host:5432/munger_test"
    assert s.dbos_system_schema == "dbos"
    assert s.dbos_app_name == "munger"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd munger/backend && pytest tests/unit/test_config_orchestrator.py::test_dbos_system_database_url_derived_from_database_url -v`
Expected: FAIL with `AttributeError: 'Settings' object has no attribute 'dbos_system_database_url'`

- [ ] **Step 3: Add the fields and derivation**

In `munger/backend/app/core/config.py`, after the `ingest_allow_null_embedding` field (line ~92), add:

```python
    # DBOS durable execution (SP1). System state lives in a schema inside the app DB.
    dbos_app_name: str = Field(default="munger", alias="DBOS_APP_NAME")
    dbos_system_schema: str = Field(default="dbos", alias="DBOS_SYSTEM_SCHEMA")
    dbos_system_database_url: Optional[str] = Field(default=None, alias="DBOS_SYSTEM_DATABASE_URL")
```

In the `__init__` method, after the `checkpointer_url` derivation block (line ~152), add:

```python
        if not self.dbos_system_database_url and self.database_url.startswith("postgresql"):
            self.dbos_system_database_url = self.database_url.replace(
                "postgresql+psycopg://", "postgresql://", 1
            )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd munger/backend && pytest tests/unit/test_config_orchestrator.py::test_dbos_system_database_url_derived_from_database_url -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add munger/backend/app/core/config.py munger/backend/tests/unit/test_config_orchestrator.py
git commit -m "feat(config): derive DBOS system database URL from DATABASE_URL"
```

---

## Task 3: Validate `ingest_orchestrator` accepts only graph | agent | dbos

**Files:**
- Modify: `munger/backend/app/core/config.py`
- Test: `munger/backend/tests/unit/test_config_orchestrator.py`

- [ ] **Step 1: Write the failing test**

Append to `munger/backend/tests/unit/test_config_orchestrator.py`:

```python
import pytest


def test_orchestrator_accepts_dbos():
    assert Settings(INGEST_ORCHESTRATOR="dbos").ingest_orchestrator == "dbos"


def test_orchestrator_accepts_graph_and_agent():
    assert Settings(INGEST_ORCHESTRATOR="graph").ingest_orchestrator == "graph"
    assert Settings(INGEST_ORCHESTRATOR="agent").ingest_orchestrator == "agent"


def test_orchestrator_rejects_unknown():
    with pytest.raises(ValueError):
        Settings(INGEST_ORCHESTRATOR="bogus")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd munger/backend && pytest tests/unit/test_config_orchestrator.py -k orchestrator -v`
Expected: `test_orchestrator_rejects_unknown` FAILS (no validator yet; `bogus` is accepted).

- [ ] **Step 3: Add the validator**

In `munger/backend/app/core/config.py`, update the comment on the `ingest_orchestrator` field (line ~85) to:

```python
    # Ingest orchestrator: "graph" (LangGraph subgraphs, default) | "agent" (legacy) | "dbos" (durable spine)
    ingest_orchestrator: str = Field(default="graph", alias="INGEST_ORCHESTRATOR")
```

Add a validator method after `validate_openrouter_embedding_model` (line ~140):

```python
    @model_validator(mode="after")
    def validate_ingest_orchestrator(self) -> "Settings":
        allowed = {"graph", "agent", "dbos"}
        if self.ingest_orchestrator not in allowed:
            raise ValueError(
                f"INGEST_ORCHESTRATOR={self.ingest_orchestrator!r} must be one of {sorted(allowed)}"
            )
        return self
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd munger/backend && pytest tests/unit/test_config_orchestrator.py -k orchestrator -v`
Expected: PASS (all 3)

- [ ] **Step 5: Commit**

```bash
git add munger/backend/app/core/config.py munger/backend/tests/unit/test_config_orchestrator.py
git commit -m "feat(config): validate INGEST_ORCHESTRATOR includes dbos"
```

---

## Task 4: Create the DBOS singleton module

**Files:**
- Create: `munger/backend/app/runtime/dbos_app.py`
- Test: `munger/backend/tests/integration/test_dbos_ingest.py`

- [ ] **Step 1: Write the failing test**

Create `munger/backend/tests/integration/test_dbos_ingest.py`:

```python
from app.core.config import get_settings
from app.runtime.dbos_app import get_dbos, launch_dbos, destroy_dbos


def test_get_dbos_is_idempotent_and_launches():
    settings = get_settings()
    d1 = get_dbos(settings)
    d2 = get_dbos(settings)
    assert d1 is d2  # singleton
    launch_dbos(settings)  # must not raise against test Postgres
    destroy_dbos()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd munger/backend && pytest tests/integration/test_dbos_ingest.py::test_get_dbos_is_idempotent_and_launches -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.runtime.dbos_app'`

- [ ] **Step 3: Write the module**

Create `munger/backend/app/runtime/dbos_app.py`:

```python
"""DBOS Transact singleton for Munger's durable ingest spine (SP1).

DBOS state lives in a dedicated schema (default ``dbos``) inside the application
Postgres database, so no separate database or server is required.
"""

from __future__ import annotations

import logging
import threading

from dbos import DBOS, DBOSConfig

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_instance: DBOS | None = None
_launched = False


def get_dbos(settings: Settings | None = None) -> DBOS:
    """Return the process-wide DBOS instance, creating it once."""
    global _instance
    if _instance is not None:
        return _instance
    with _lock:
        if _instance is None:
            settings = settings or get_settings()
            config: DBOSConfig = {
                "name": settings.dbos_app_name,
                "system_database_url": settings.dbos_system_database_url,
                "dbos_system_schema": settings.dbos_system_schema,
            }
            _instance = DBOS(config=config)
            logger.info("DBOS configured (schema=%s)", settings.dbos_system_schema)
    return _instance


def launch_dbos(settings: Settings | None = None) -> None:
    """Launch DBOS exactly once. Safe to call repeatedly."""
    global _launched
    if _launched:
        return
    with _lock:
        if not _launched:
            get_dbos(settings)
            DBOS.launch()
            _launched = True
            logger.info("DBOS launched")


def destroy_dbos() -> None:
    """Tear down DBOS (used by tests)."""
    global _instance, _launched
    with _lock:
        if _instance is not None:
            DBOS.destroy()
        _instance = None
        _launched = False
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd munger/backend && pytest tests/integration/test_dbos_ingest.py::test_get_dbos_is_idempotent_and_launches -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add munger/backend/app/runtime/dbos_app.py munger/backend/tests/integration/test_dbos_ingest.py
git commit -m "feat(runtime): add DBOS singleton (configure/launch/destroy)"
```

---

## Task 5: Define the durable ingest workflow (strangler wrap)

**Files:**
- Create: `munger/backend/app/runtime/dbos_ingest.py`
- Modify: `munger/backend/app/runtime/ingest_runner.py` (add `orchestrator` override — see Step 3)
- Test: `munger/backend/tests/integration/test_dbos_ingest.py`

- [ ] **Step 1: Write the failing test**

Append to `munger/backend/tests/integration/test_dbos_ingest.py`:

```python
from app.runtime.dbos_app import launch_dbos, destroy_dbos
from app.runtime.dbos_ingest import ingest_source_workflow


def test_workflow_runs_and_returns_status(create_source):
    # LLM is unavailable in tests (ollama@127.0.0.1:9), so the pipeline fails fast
    # through the SAME guard the graph path uses — proving the wrap reuses it.
    source = create_source(status="pending", content_text="hello world")
    launch_dbos()
    try:
        result = ingest_source_workflow(source.id, None)
    finally:
        destroy_dbos()
    assert result["source_id"] == source.id
    assert result["status"] == "failed"
    assert "LLM service not available" in (result.get("error") or "")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd munger/backend && pytest tests/integration/test_dbos_ingest.py::test_workflow_runs_and_returns_status -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.runtime.dbos_ingest'`

- [ ] **Step 3: Add the `orchestrator` override to IngestRunner.run**

In `munger/backend/app/runtime/ingest_runner.py`, change the `run` signature (line 82) and its branch (line 104). Replace:

```python
    async def run(self, source_id: int, job_id: int | None = None) -> IngestRunState:
        logger.info(
            "Starting ingest for source %s (job=%s, orchestrator=%s)",
            source_id,
            job_id,
            self.settings.ingest_orchestrator,
        )
```

with:

```python
    async def run(
        self,
        source_id: int,
        job_id: int | None = None,
        orchestrator: str | None = None,
    ) -> IngestRunState:
        orchestrator = orchestrator or self.settings.ingest_orchestrator
        logger.info(
            "Starting ingest for source %s (job=%s, orchestrator=%s)",
            source_id,
            job_id,
            orchestrator,
        )
```

Then replace the branch (line 104):

```python
        if self.settings.ingest_orchestrator == "graph":
            return await self._run_graph(
                source_id=source_id,
                job_id=job_id,
                services=services,
                checkpointer=checkpointer,
            )

        return await self._run_agent(
```

with:

```python
        if orchestrator == "dbos":
            from app.runtime.dbos_ingest import run_via_dbos

            return await run_via_dbos(source_id, job_id)

        if orchestrator == "graph":
            return await self._run_graph(
                source_id=source_id,
                job_id=job_id,
                services=services,
                checkpointer=checkpointer,
            )

        return await self._run_agent(
```

- [ ] **Step 4: Write the workflow module**

Create `munger/backend/app/runtime/dbos_ingest.py`:

```python
"""Durable DBOS workflow wrapping the existing ingest pipeline (SP1.1).

Strangler step: the workflow runs the current async pipeline (forced to the
``graph`` orchestrator to avoid recursing back into DBOS) inside a single
durable step. Later sub-projects (SP1.2) decompose this into per-stage steps.
"""

from __future__ import annotations

import asyncio
import logging

from dbos import DBOS

from app.core.config import get_settings
from app.runtime.ingest_runner import IngestRunner
from app.runtime.state import IngestRunState

logger = logging.getLogger(__name__)


async def _run_pipeline_async(source_id: int, job_id: int | None) -> IngestRunState:
    # Force "graph" so we reuse the existing pipeline and never recurse into dbos.
    runner = IngestRunner(get_settings())
    return await runner.run(source_id, job_id=job_id, orchestrator="graph")


@DBOS.step()
def ingest_pipeline_step(source_id: int, job_id: int | None) -> IngestRunState:
    # DBOS runs steps in their own threads (no running event loop), so asyncio.run is safe.
    return asyncio.run(_run_pipeline_async(source_id, job_id))


@DBOS.workflow()
def ingest_source_workflow(source_id: int, job_id: int | None) -> IngestRunState:
    return ingest_pipeline_step(source_id, job_id)


async def run_via_dbos(source_id: int, job_id: int | None) -> IngestRunState:
    """Start the durable workflow from async code, bridging to DBOS's sync API."""
    loop = asyncio.get_running_loop()

    def _start_and_wait() -> IngestRunState:
        handle = DBOS.start_workflow(ingest_source_workflow, source_id, job_id)
        return handle.get_result()

    return await loop.run_in_executor(None, _start_and_wait)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd munger/backend && pytest tests/integration/test_dbos_ingest.py::test_workflow_runs_and_returns_status -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add munger/backend/app/runtime/dbos_ingest.py munger/backend/app/runtime/ingest_runner.py
git commit -m "feat(runtime): durable DBOS ingest workflow behind orchestrator flag"
```

---

## Task 6: Route the `dbos` orchestrator end-to-end via IngestRunner

**Files:**
- Test: `munger/backend/tests/integration/test_dbos_ingest.py`

- [ ] **Step 1: Write the failing test**

Append to `munger/backend/tests/integration/test_dbos_ingest.py`:

```python
from app.core.config import Settings
from app.runtime.ingest_runner import IngestRunner
from app.runtime.dbos_app import launch_dbos, destroy_dbos


def test_runner_routes_to_dbos(create_source):
    import asyncio as _asyncio

    source = create_source(status="pending", content_text="routing test")
    settings = Settings(INGEST_ORCHESTRATOR="dbos")
    launch_dbos(settings)
    try:
        result = _asyncio.run(IngestRunner(settings).run(source.id, job_id=None))
    finally:
        destroy_dbos()
    # Same fail-fast guard as the graph path, reached through the DBOS workflow.
    assert result["source_id"] == source.id
    assert result["status"] == "failed"
```

- [ ] **Step 2: Run test to verify it fails or passes**

Run: `cd munger/backend && pytest tests/integration/test_dbos_ingest.py::test_runner_routes_to_dbos -v`
Expected: PASS (Task 5 already wired `run()` → `run_via_dbos`). If FAIL, the `orchestrator == "dbos"` branch in `ingest_runner.py` is missing — re-check Task 5 Step 3.

- [ ] **Step 3: No new implementation needed**

This task verifies the wiring from Task 5. If Step 2 passed, proceed.

- [ ] **Step 4: Commit**

```bash
git add munger/backend/tests/integration/test_dbos_ingest.py
git commit -m "test(runtime): verify dbos orchestrator routing end-to-end"
```

---

## Task 7: Launch DBOS once at worker startup

**Files:**
- Modify: `munger/backend/app/worker/runner.py`

- [ ] **Step 1: Write the failing test**

Append to `munger/backend/tests/integration/test_dbos_ingest.py`:

```python
def test_worker_launches_dbos_when_orchestrator_is_dbos(monkeypatch):
    import app.worker.runner as worker_runner
    from app.runtime import dbos_app

    launched = {"called": False}

    def _fake_launch(settings=None):
        launched["called"] = True

    monkeypatch.setattr(dbos_app, "launch_dbos", _fake_launch)
    monkeypatch.setattr(worker_runner, "launch_dbos", _fake_launch, raising=False)
    worker_runner.maybe_launch_dbos(
        type("S", (), {"ingest_orchestrator": "dbos"})()
    )
    assert launched["called"] is True


def test_worker_skips_dbos_when_orchestrator_is_graph(monkeypatch):
    import app.worker.runner as worker_runner

    launched = {"called": False}
    monkeypatch.setattr(
        worker_runner, "launch_dbos", lambda settings=None: launched.__setitem__("called", True)
    )
    worker_runner.maybe_launch_dbos(
        type("S", (), {"ingest_orchestrator": "graph"})()
    )
    assert launched["called"] is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd munger/backend && pytest tests/integration/test_dbos_ingest.py -k worker -v`
Expected: FAIL with `AttributeError: module 'app.worker.runner' has no attribute 'maybe_launch_dbos'`

- [ ] **Step 3: Add the launch hook**

In `munger/backend/app/worker/runner.py`, add an import near the top (after line 11):

```python
from app.runtime.dbos_app import launch_dbos
```

Add this helper above `run_worker_forever` (line ~60):

```python
def maybe_launch_dbos(settings) -> None:
    """Launch DBOS once if the durable orchestrator is selected."""
    if settings.ingest_orchestrator == "dbos":
        launch_dbos(settings)
        logger.info("DBOS launched for worker (orchestrator=dbos)")
```

Inside `run_worker_forever`, after `settings = get_settings()` (line 61), add:

```python
    maybe_launch_dbos(settings)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd munger/backend && pytest tests/integration/test_dbos_ingest.py -k worker -v`
Expected: PASS (both)

- [ ] **Step 5: Commit**

```bash
git add munger/backend/app/worker/runner.py munger/backend/tests/integration/test_dbos_ingest.py
git commit -m "feat(worker): launch DBOS at startup when orchestrator=dbos"
```

---

## Task 8: Full regression + durability sanity check

**Files:** none (verification only)

- [ ] **Step 1: Run the full backend suite to confirm no regression**

Run: `cd munger/backend && pytest tests/ -q`
Expected: all tests pass. The default `INGEST_ORCHESTRATOR=graph` path is untouched, so existing ingest tests must remain green.

- [ ] **Step 2: Confirm DBOS persisted workflow state (durability evidence)**

Run:

```bash
cd munger/backend && python - <<'PY'
import os
from sqlalchemy import create_engine, text
url = os.environ["TEST_DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://", 1)
eng = create_engine(url)
with eng.connect() as c:
    rows = c.execute(text(
        "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'dbos'"
    )).scalar()
print("dbos schema tables:", rows)
PY
```

Expected: prints a non-zero count — DBOS created its system tables in the `dbos` schema of the same database (proving "Postgres is all you need").

- [ ] **Step 3: Final commit (if any docs/notes changed)**

```bash
git add -A
git commit -m "chore(sp1): DBOS spine foundation verified green" --allow-empty
```

---

## Self-Review

**Spec coverage (against `docs/superpowers/specs/2026-06-09-munger-data-architecture-design.md` §11 SP1):** This plan delivers the *foundation* slice of SP1 — the DBOS orchestrator path behind `INGEST_ORCHESTRATOR`, with parity preserved (graph path untouched; dbos path reuses it). Deferred to follow-up plans, as the spec's decomposition intends: per-stage DBOS steps (SP1.2), vectors → LanceDB (SP1.3), schema deltas `relationship_evidence`/`canonical_entity_id`/`feedback`/`chat` (SP1.4). SP0 harness, SP2–SP5 are separate specs/plans.

**Placeholder scan:** No TBD/TODO; every code step shows complete content; commands have expected output. The one investigative step (Task 1 Step 3) is a concrete runnable spike with exact expected output, not a placeholder.

**Type/name consistency:** `get_dbos`/`launch_dbos`/`destroy_dbos` (dbos_app.py) used consistently in Tasks 4–7. `ingest_source_workflow`/`ingest_pipeline_step`/`run_via_dbos` (dbos_ingest.py) consistent between Task 5 definition and Tasks 5–6 tests. `IngestRunner.run(..., orchestrator=...)` defined in Task 5 Step 3 and used in `run_via_dbos` (`orchestrator="graph"`) and Task 6 test. `maybe_launch_dbos` defined and tested in Task 7. Config fields `dbos_app_name`/`dbos_system_schema`/`dbos_system_database_url` defined in Task 2, consumed in Task 4.

**Known residual risk:** DBOS async-API maturity is sidestepped by using the sync workflow + `asyncio.run`-in-step + executor bridge pattern, validated empirically in Task 1 Step 3 before any code depends on it. If that spike fails, stop and revisit (the fallback is DBOS async workflows, which would change Task 5 only).
