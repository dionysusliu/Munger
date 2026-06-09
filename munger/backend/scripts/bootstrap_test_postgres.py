#!/usr/bin/env python3
"""Bootstrap munger_test database for pytest (Postgres only)."""

from __future__ import annotations

import os
import runpy
from pathlib import Path

os.environ.setdefault("MUNGER_POSTGRES_APP_DB", "munger_test")
runpy.run_path(str(Path(__file__).parent / "bootstrap_postgres.py"), run_name="__main__")
