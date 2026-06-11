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
    # get_dbos must be called OUTSIDE the _lock block: get_dbos also acquires
    # _lock when _instance is None, and threading.Lock is not re-entrant.
    # Calling it here first is safe because get_dbos is internally thread-safe.
    get_dbos(settings)
    with _lock:
        if not _launched:
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
