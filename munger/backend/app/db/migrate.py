"""Run Alembic migrations programmatically."""

from __future__ import annotations

import logging
from pathlib import Path

from alembic import command
from alembic.config import Config

logger = logging.getLogger(__name__)


def run_migrations() -> None:
    backend_root = Path(__file__).resolve().parents[2]
    alembic_ini = backend_root / "alembic.ini"
    cfg = Config(str(alembic_ini))
    cfg.set_main_option("script_location", str(backend_root / "alembic"))
    command.upgrade(cfg, "head")
    logger.info("Alembic migrations applied")
