"""Tests for per-chunk map status helpers."""

import asyncio

from app.services.chunk_map_status import reclaim_stale_running


def test_reclaim_stale_running_no_op_without_chunks():
    reclaimed = asyncio.run(reclaim_stale_running(source_id=999999))
    assert reclaimed == 0
