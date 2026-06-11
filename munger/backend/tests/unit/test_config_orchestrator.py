import pytest

from app.core.config import Settings


def test_dbos_system_database_url_derived_from_database_url():
    s = Settings(DATABASE_URL="postgresql+psycopg://u:p@host:5432/munger_test")
    # libpq (sync) form of the SAME database — DBOS stores its state in a schema there
    assert s.dbos_system_database_url == "postgresql://u:p@host:5432/munger_test"
    assert s.dbos_system_schema == "dbos"
    assert s.dbos_app_name == "munger"


def test_orchestrator_accepts_dbos():
    assert Settings(INGEST_ORCHESTRATOR="dbos").ingest_orchestrator == "dbos"


def test_orchestrator_accepts_graph_and_agent():
    assert Settings(INGEST_ORCHESTRATOR="graph").ingest_orchestrator == "graph"
    assert Settings(INGEST_ORCHESTRATOR="agent").ingest_orchestrator == "agent"


def test_orchestrator_rejects_unknown():
    with pytest.raises(ValueError):
        Settings(INGEST_ORCHESTRATOR="bogus")
