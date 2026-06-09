"""Optional integration tests for Postgres worker queue (requires TEST_DATABASE_URL)."""

import os

import pytest

pytestmark = pytest.mark.skipif(
    not os.environ.get("TEST_DATABASE_URL", "").startswith("postgresql"),
    reason="Set TEST_DATABASE_URL to a Postgres DSN to run worker integration tests",
)


@pytest.mark.asyncio
async def test_placeholder_worker_integration():
    """Reserved for parallel ingest + job claim integration against Postgres."""
    assert True
