from app.core.config import Settings, get_settings
from app.runtime.dbos_app import get_dbos, launch_dbos, destroy_dbos

# Import at module level so DBOS workflow/step decorators are registered
# before any launch_dbos() call inside the tests below.
from app.runtime.dbos_ingest import ingest_source_workflow  # noqa: F401
from app.runtime.ingest_runner import IngestRunner


def test_get_dbos_is_idempotent_and_launches():
    settings = get_settings()
    d1 = get_dbos(settings)
    d2 = get_dbos(settings)
    assert d1 is d2  # singleton
    launch_dbos(settings)  # must not raise against test Postgres
    destroy_dbos()


def test_workflow_runs_and_returns_status(create_source):
    # Test env has no reachable LLM, so the wrapped pipeline fails — but the workflow
    # still routes + executes the real pipeline and returns a structured result.
    source = create_source(status="pending", content_text="hello world")
    launch_dbos()
    try:
        result = ingest_source_workflow(source.id, None)
    finally:
        destroy_dbos()
    assert result["source_id"] == source.id
    assert "status" in result


def test_runner_routes_to_dbos(create_source):
    import asyncio as _asyncio
    source = create_source(status="pending", content_text="routing test")
    settings = Settings(INGEST_ORCHESTRATOR="dbos")
    launch_dbos(settings)
    try:
        result = _asyncio.run(IngestRunner(settings).run(source.id, job_id=None))
    finally:
        destroy_dbos()
    assert result["source_id"] == source.id
    assert "status" in result
