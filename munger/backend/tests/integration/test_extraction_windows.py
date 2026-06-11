"""Integration tests for extraction-window demux and K=1 identity.

LLM call ordering inside map_window (max_gleanings=0, K chunks):
  1. _contextual_prefix for chunk 0   → llm.chat()          ← script[0]
  2. _contextual_prefix for chunk 1   → llm.chat()          ← script[1]
  ...
  K. _contextual_prefix for chunk K-1 → llm.chat()          ← script[K-1]
  K+1. _extract_chunk(virtual window) → llm.chat_structured()← script[K]

This matches the original map_single_chunk ordering for K=1 (prefix before extract),
preserving backward compat with existing tests.
"""

from __future__ import annotations

import pytest
from sqlalchemy import select

from app.core.config import Settings
from app.core.database import async_session_maker
from app.models.chunk import Chunk
from app.models.chunk_extraction import ChunkExtraction
from app.models.source import Source
from app.services.chunk_map_status import MAP_DONE, MAP_FAILED
from app.services.chunk_service import ChunkService
from app.services.map_chunk_service import MapChunkService
from tests.conftest import run_async
from tests.fixtures.fake_llm import ScriptedLLMService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _settings(max_gleanings: int = 0) -> Settings:
    return Settings(
        ingest_orchestrator="graph",
        ingest_map_mode="service",
        ingest_max_gleanings=max_gleanings,
        ingest_allow_null_embedding=False,
    )


def _make_service(scripts: list, settings: Settings) -> MapChunkService:
    llm = ScriptedLLMService(scripts=scripts)
    chunk_svc = ChunkService(llm_service=llm, settings=settings)
    return MapChunkService(llm_service=llm, chunk_service=chunk_svc, settings=settings)


async def _seed(
    content_text: str,
    chunk_specs: list[tuple[int, int, int]],
) -> tuple[int, list[int]]:
    """Seed Source + hand-built Chunk rows. Returns (source_id, [chunk_id, ...])."""
    async with async_session_maker() as session:
        source = Source(
            title="Window Test Source",
            filename="win.txt",
            file_path="sources/win.txt",
            file_type="txt",
            content_hash="hash-win-test",
            file_size=len(content_text.encode()),
            content_text=content_text,
            status="extracting",
        )
        session.add(source)
        await session.flush()
        source_id = source.id

        chunk_ids: list[int] = []
        for idx, start, end in chunk_specs:
            chunk = Chunk(
                source_id=source_id,
                chunk_index=idx,
                content=content_text[start:end],
                token_count=end - start,
                doc_char_start=start,
                doc_char_end=end,
                map_status="pending",
            )
            session.add(chunk)
            await session.flush()
            chunk_ids.append(chunk.id)

        await session.commit()
        return source_id, chunk_ids


# ---------------------------------------------------------------------------
# Test 1 — demux: entities land in their owning chunk's row
# ---------------------------------------------------------------------------


def test_window_demux_attributes_entities_to_owning_chunks():
    """K=3 window: entities at doc-global offsets 10 and 120 demux to chunk 0 and chunk 2.

    Setup
    -----
    content_text: 150 chars (50×A + 50×B + 50×C).
    Chunks (with overlap, all pending):
      chunk 0: doc_char [0,  80)
      chunk 1: doc_char [50, 120)
      chunk 2: doc_char [100, 150)
    window_text = content_text[0:150], offset_base = 0.

    LLM script (max_gleanings=0)
    ----------------------------
      script[0]: "prefix0"           ← _contextual_prefix chunk 0
      script[1]: "prefix1"           ← _contextual_prefix chunk 1
      script[2]: "prefix2"           ← _contextual_prefix chunk 2
      script[3]: extraction dict     ← _extract_chunk(virtual_window)

    Extraction returns:
      Entity A  char_start=10  → 0 ≤ 10 < 80  → chunk 0
      Entity C  char_start=120 → 100 ≤ 120 < 150 → chunk 2
      Relationship              → always first claimed chunk (chunk 0)

    Expectations
    ------------
    • 3 ChunkExtraction round-0 rows (one per claimed chunk, even if empty)
    • chunk 0: entities=[Entity A], relationships=[rel]
    • chunk 1: entities=[], relationships=[]
    • chunk 2: entities=[Entity C], relationships=[]
    • All 3 chunks → MAP_DONE
    """
    content_text = "A" * 50 + "B" * 50 + "C" * 50  # 150 chars
    chunk_specs = [(0, 0, 80), (1, 50, 120), (2, 100, 150)]

    scripts = [
        "prefix0",  # script[0]: prefix for chunk 0
        "prefix1",  # script[1]: prefix for chunk 1
        "prefix2",  # script[2]: prefix for chunk 2
        {           # script[3]: extraction (window-relative = doc-global when base=0)
            "entities": [
                {
                    "name": "Entity A",
                    "type": "concept",
                    "description": "lives in chunk 0",
                    "char_start": 10,
                    "char_end": 20,
                },
                {
                    "name": "Entity C",
                    "type": "concept",
                    "description": "lives in chunk 2",
                    "char_start": 120,
                    "char_end": 130,
                },
            ],
            "relationships": [
                {
                    "source": "Entity A",
                    "target": "Entity C",
                    "type": "relates_to",
                    "description": "connected",
                }
            ],
        },
    ]

    settings = _settings(max_gleanings=0)
    svc = _make_service(scripts, settings)

    async def _run():
        source_id, chunk_ids = await _seed(content_text, chunk_specs)
        c0_id, c1_id, c2_id = chunk_ids

        result = await svc.map_window(chunk_ids, source_id)

        # --- return-value assertions ---
        assert result.get("entities_raw") == 2, f"Expected 2 entities, got {result}"
        assert result.get("relationships_raw") == 1, f"Expected 1 rel, got {result}"
        assert result.get("glean_entities_added") == 0
        assert "skipped" not in result

        # --- per-chunk ChunkExtraction rows ---
        async with async_session_maker() as session:
            rows = list(
                (
                    await session.execute(
                        select(ChunkExtraction)
                        .where(ChunkExtraction.source_id == source_id)
                        .order_by(ChunkExtraction.chunk_id)
                    )
                )
                .scalars()
                .all()
            )

        assert len(rows) == 3, (
            f"Expected 3 ChunkExtraction rows (one per claimed chunk), got {len(rows)}"
        )
        by_chunk = {r.chunk_id: r for r in rows}

        # chunk 0: Entity A + relationship
        r0 = by_chunk[c0_id]
        assert r0.glean_round == 0
        assert len(r0.entities) == 1, f"chunk 0 should have 1 entity; got {r0.entities}"
        assert r0.entities[0]["name"] == "Entity A"
        assert r0.entities[0]["char_start"] == 10, "char_start must be doc-global"
        assert len(r0.relationships) == 1, "relationship must go to first chunk"

        # chunk 1: empty row (still must exist)
        r1 = by_chunk[c1_id]
        assert r1.glean_round == 0
        assert len(r1.entities) == 0, f"chunk 1 should be empty; got {r1.entities}"
        assert len(r1.relationships) == 0

        # chunk 2: Entity C
        r2 = by_chunk[c2_id]
        assert r2.glean_round == 0
        assert len(r2.entities) == 1, f"chunk 2 should have 1 entity; got {r2.entities}"
        assert r2.entities[0]["name"] == "Entity C"
        assert r2.entities[0]["char_start"] == 120, "char_start must be doc-global"
        assert len(r2.relationships) == 0

        # --- all chunks MAP_DONE ---
        async with async_session_maker() as session:
            chunks = list(
                (
                    await session.execute(
                        select(Chunk).where(Chunk.source_id == source_id)
                    )
                )
                .scalars()
                .all()
            )
        assert all(c.map_status == MAP_DONE for c in chunks), (
            f"Expected all MAP_DONE; got {[c.map_status for c in chunks]}"
        )

    run_async(_run())


# ---------------------------------------------------------------------------
# Test 2 — K=1 identity: map_single_chunk produces same result as legacy
# ---------------------------------------------------------------------------


def test_window_of_one_equals_legacy():
    """map_single_chunk on one pending chunk delegates to map_window([id]) and
    produces exactly one round-0 ChunkExtraction row, status MAP_DONE.

    Script ordering (K=1, max_gleanings=0):
      script[0]: "ctx prefix"     ← _contextual_prefix
      script[1]: extraction dict  ← _extract_chunk(virtual_window)

    This matches the ORIGINAL map_single_chunk ordering (prefix before extract),
    confirming the refactor does not change the LLM call sequence for K=1.
    """
    content_text = "Charlie Munger advocates Mental Models as a latticework for decisions."
    chunk_specs = [(0, 0, len(content_text))]

    scripts = [
        "Munger document context.",  # script[0]: prefix
        {                            # script[1]: extraction
            "entities": [
                {
                    "name": "Charlie Munger",
                    "type": "person",
                    "description": "Investor",
                    "char_start": 0,
                    "char_end": 14,
                },
            ],
            "relationships": [],
        },
    ]

    settings = _settings(max_gleanings=0)
    svc = _make_service(scripts, settings)

    async def _run():
        source_id, chunk_ids = await _seed(content_text, chunk_specs)
        (chunk_id,) = chunk_ids

        # Call through map_single_chunk (the public wrapper) to test the full K=1 path
        result = await svc.map_single_chunk(chunk_id, source_id)

        assert result.get("entities_raw") == 1
        assert result.get("relationships_raw") == 0
        assert result.get("glean_entities_added") == 0
        assert "skipped" not in result

        # Exactly one ChunkExtraction row (round 0)
        async with async_session_maker() as session:
            rows = list(
                (
                    await session.execute(
                        select(ChunkExtraction).where(ChunkExtraction.source_id == source_id)
                    )
                )
                .scalars()
                .all()
            )

        assert len(rows) == 1, f"Expected 1 ChunkExtraction row, got {len(rows)}"
        assert rows[0].glean_round == 0
        assert len(rows[0].entities) == 1
        assert rows[0].entities[0]["name"] == "Charlie Munger"

        # Chunk is MAP_DONE with an embedding
        async with async_session_maker() as session:
            chunk = await session.get(Chunk, chunk_id)
        assert chunk.map_status == MAP_DONE
        assert chunk.embedding is not None, "map_single_chunk must embed the chunk"

    run_async(_run())


# ---------------------------------------------------------------------------
# Test 3 — failure: LLM raises → all window chunks MAP_FAILED
# ---------------------------------------------------------------------------


def test_window_failure_marks_all_failed():
    """If _extract_chunk raises, map_window must mark ALL claimed chunks MAP_FAILED
    and re-raise the exception.

    Setup: 2 chunks, both pending. FailingLLMService.chat_structured raises RuntimeError.
    _contextual_prefix uses llm.chat() (not chat_structured) → falls back to empty string.
    Extraction is the first chat_structured call → raises immediately.
    """

    class FailingLLMService(ScriptedLLMService):
        async def chat_structured(self, messages, response_model, **kwargs):
            raise RuntimeError("Simulated LLM failure for window")

    content_text = "A" * 100 + "B" * 100
    chunk_specs = [(0, 0, 100), (1, 80, 200)]

    llm = FailingLLMService(scripts=[])
    settings = _settings(max_gleanings=0)
    chunk_svc = ChunkService(llm_service=llm, settings=settings)
    svc = MapChunkService(llm_service=llm, chunk_service=chunk_svc, settings=settings)

    async def _run():
        source_id, chunk_ids = await _seed(content_text, chunk_specs)

        with pytest.raises(RuntimeError, match="Simulated LLM failure for window"):
            await svc.map_window(chunk_ids, source_id)

        # Both chunks must be MAP_FAILED
        async with async_session_maker() as session:
            chunks = list(
                (
                    await session.execute(
                        select(Chunk).where(Chunk.source_id == source_id)
                    )
                )
                .scalars()
                .all()
            )

        statuses = [c.map_status for c in chunks]
        assert all(s == MAP_FAILED for s in statuses), (
            f"Expected all MAP_FAILED after LLM failure; got {statuses}"
        )

    run_async(_run())


# ---------------------------------------------------------------------------
# Test 4 — offset-less entities fall to first claimed chunk
# ---------------------------------------------------------------------------


def test_offsetless_entities_fall_to_first_chunk():
    """Entities with char_start=None (no doc offset) must be assigned to the
    first claimed chunk, not dropped.

    Setup: 2 chunks, extraction returns one entity with no char_start/char_end.

    Script ordering (K=2, max_gleanings=0):
      script[0]: "prefix0"      ← _contextual_prefix chunk 0
      script[1]: "prefix1"      ← _contextual_prefix chunk 1
      script[2]: extraction dict ← _extract_chunk(virtual_window)
    """
    content_text = "X" * 50 + "Y" * 50
    chunk_specs = [(0, 0, 50), (1, 40, 100)]

    scripts = [
        "prefix0",  # script[0]
        "prefix1",  # script[1]
        {           # script[2]: entity with no char offsets
            "entities": [
                {
                    "name": "Orphan Entity",
                    "type": "concept",
                    "description": "no char offset provided",
                    # char_start and char_end omitted → Pydantic defaults them to None
                },
            ],
            "relationships": [],
        },
    ]

    settings = _settings(max_gleanings=0)
    svc = _make_service(scripts, settings)

    async def _run():
        source_id, chunk_ids = await _seed(content_text, chunk_specs)
        c0_id, c1_id = chunk_ids

        result = await svc.map_window(chunk_ids, source_id)

        assert result.get("entities_raw") == 1
        assert result.get("relationships_raw") == 0

        # 2 claimed chunks → 2 round-0 rows
        async with async_session_maker() as session:
            rows = list(
                (
                    await session.execute(
                        select(ChunkExtraction).where(ChunkExtraction.source_id == source_id)
                    )
                )
                .scalars()
                .all()
            )

        assert len(rows) == 2, f"Expected 2 ChunkExtraction rows, got {len(rows)}"
        by_chunk = {r.chunk_id: r for r in rows}

        # First chunk gets the offset-less entity
        r0 = by_chunk[c0_id]
        assert len(r0.entities) == 1, (
            f"Offset-less entity must go to first chunk; got {r0.entities}"
        )
        assert r0.entities[0]["name"] == "Orphan Entity"

        # Second chunk is empty
        r1 = by_chunk[c1_id]
        assert len(r1.entities) == 0, (
            f"Second chunk must be empty; got {r1.entities}"
        )

        # Both chunks MAP_DONE
        async with async_session_maker() as session:
            chunks = list(
                (
                    await session.execute(
                        select(Chunk).where(Chunk.source_id == source_id)
                    )
                )
                .scalars()
                .all()
            )
        assert all(c.map_status == MAP_DONE for c in chunks)

    run_async(_run())


# ---------------------------------------------------------------------------
# Test 5 — fanout grouping: fanout_chunks sends window-grouped chunk_ids
# ---------------------------------------------------------------------------


def test_send_fanout_groups_windows():
    """_group_windows partitions IDs into windows of K; fanout_chunks uses chunk_ids payload key.

    Verifies:
    - _group_windows([10,20,30,40,50], 2) == [[10,20],[30,40],[50]]  (3 windows)
    - _group_windows([10,20,30,40,50], 1) == 5 singletons
    - fanout_chunks over 5 IDs with K=2 emits 3 Sends, each with "chunk_ids" key (not "chunk_id")
    """
    from unittest.mock import MagicMock

    from app.runtime.graphs.nodes.nodes_cognify import _group_windows, make_cognify_nodes

    ids = [10, 20, 30, 40, 50]

    # --- _group_windows unit assertions ---
    assert _group_windows(ids, 2) == [[10, 20], [30, 40], [50]], (
        f"K=2 grouping wrong: {_group_windows(ids, 2)}"
    )
    assert _group_windows(ids, 1) == [[10], [20], [30], [40], [50]], (
        f"K=1 must produce 5 singletons: {_group_windows(ids, 1)}"
    )

    # --- fanout_chunks payload shape ---
    settings = MagicMock()
    settings.ingest_extraction_window_chunks = 2
    mock_services = MagicMock()
    mock_services.settings = settings

    nodes = make_cognify_nodes(mock_services)
    fanout = nodes["fanout_chunks"]

    state = {"chunk_ids": ids, "source_id": 99, "job_id": 1}
    sends = fanout(state)

    assert len(sends) == 3, f"Expected 3 Sends for K=2 over 5 ids, got {len(sends)}"
    for send in sends:
        assert "chunk_ids" in send.arg, f"Send payload must use 'chunk_ids' key: {send.arg}"
        assert "chunk_id" not in send.arg, f"Send payload must NOT use old 'chunk_id' key: {send.arg}"

    assert sends[0].arg["chunk_ids"] == [10, 20], f"Window 0 wrong: {sends[0].arg}"
    assert sends[1].arg["chunk_ids"] == [30, 40], f"Window 1 wrong: {sends[1].arg}"
    assert sends[2].arg["chunk_ids"] == [50], f"Window 2 (tail) wrong: {sends[2].arg}"


# ---------------------------------------------------------------------------
# Test 6 — partial claim: non-consecutive claimed chunks form separate runs
# ---------------------------------------------------------------------------


def test_partial_claim_splits_into_runs_and_skips_unclaimed_text():
    """3 consecutive chunks; middle one pre-marked 'running' (another worker owns it).

    map_window([c0, c1, c2]) must:
    - process runs [c0] and [c2] with SEPARATE extract calls
    - each extract prompt contains ONLY that run's text (never c1's B-text)
    - write ChunkExtraction rows for c0 and c2 only (c1 gets zero rows)
    - leave c1 untouched (still 'running')
    - mark c0 and c2 MAP_DONE

    Content layout (90 chars):
      c0: "A" * 30  doc_char [0,  30)  chunk_index=0
      c1: "B" * 30  doc_char [30, 60)  chunk_index=1  ← pre-running, not claimed
      c2: "C" * 30  doc_char [60, 90)  chunk_index=2

    Script ordering (max_gleanings=0, 2 runs × 1 chunk each):
      script[0]: "prefix0"       ← _contextual_prefix for c0
      script[1]: extraction dict ← _extract_chunk(run [c0])
      script[2]: "prefix2"       ← _contextual_prefix for c2
      script[3]: extraction dict ← _extract_chunk(run [c2])
    """
    from sqlalchemy import update as sa_update

    content_text = "A" * 30 + "B" * 30 + "C" * 30  # 90 chars
    chunk_specs = [
        (0,  0, 30),   # c0: chunk_index=0
        (1, 30, 60),   # c1: chunk_index=1  — will be pre-marked running
        (2, 60, 90),   # c2: chunk_index=2
    ]
    c1_text = "B" * 30  # must never appear in any extract prompt

    class RecordingScriptedLLM(ScriptedLLMService):
        """Captures every user-role message routed through chat()."""

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.captured_user_messages: list[str] = []

        async def chat(self, messages: list[dict], **kwargs) -> str:
            for m in messages:
                if m.get("role") == "user":
                    self.captured_user_messages.append(m["content"])
            return await super().chat(messages, **kwargs)

    scripts = [
        "prefix0",       # script[0]: _contextual_prefix for c0
        {                # script[1]: extraction for run [c0] (text = "A"*30)
            "entities": [
                {
                    "name": "EntityA",
                    "type": "concept",
                    "description": "in c0",
                    "char_start": 5,    # run-relative; offset_base=0 → doc-global=5
                    "char_end": 10,
                },
            ],
            "relationships": [],
        },
        "prefix2",       # script[2]: _contextual_prefix for c2
        {                # script[3]: extraction for run [c2] (text = "C"*30)
            "entities": [
                {
                    "name": "EntityC",
                    "type": "concept",
                    "description": "in c2",
                    "char_start": 5,    # run-relative; offset_base=60 → doc-global=65
                    "char_end": 10,
                },
            ],
            "relationships": [],
        },
    ]

    settings = _settings(max_gleanings=0)
    llm = RecordingScriptedLLM(scripts=scripts)
    chunk_svc = ChunkService(llm_service=llm, settings=settings)
    svc = MapChunkService(llm_service=llm, chunk_service=chunk_svc, settings=settings)

    async def _run():
        source_id, chunk_ids = await _seed(content_text, chunk_specs)
        c0_id, c1_id, c2_id = chunk_ids

        # Pre-mark c1 as 'running' — simulates another worker having claimed it
        async with async_session_maker() as session:
            await session.execute(
                sa_update(Chunk).where(Chunk.id == c1_id).values(map_status="running")
            )
            await session.commit()

        result = await svc.map_window(chunk_ids, source_id)

        # --- Return-value assertions ---
        # 1 entity from c0's run + 1 entity from c2's run = 2 total
        assert result.get("entities_raw") == 2, (
            f"Expected 2 entities total (1 per run); got {result}"
        )
        assert result.get("relationships_raw") == 0
        assert result.get("glean_entities_added") == 0
        assert "skipped" not in result

        # --- c1 text must NOT appear in any extract prompt ---
        extract_msgs = [
            m for m in llm.captured_user_messages if "Document offset base:" in m
        ]
        assert len(extract_msgs) == 2, (
            f"Expected exactly 2 extract calls (one per claimed run); got {len(extract_msgs)}"
        )
        for msg in extract_msgs:
            assert c1_text not in msg, (
                f"c1 text ('B'*30) must not appear in any extract prompt; "
                f"found in: {msg[:120]!r}"
            )

        # --- ChunkExtraction rows: c0 and c2 only, c1 untouched ---
        async with async_session_maker() as session:
            rows = list(
                (
                    await session.execute(
                        select(ChunkExtraction).where(ChunkExtraction.source_id == source_id)
                    )
                )
                .scalars()
                .all()
            )
        row_chunk_ids = {r.chunk_id for r in rows}
        assert c0_id in row_chunk_ids, "c0 must have a ChunkExtraction row"
        assert c2_id in row_chunk_ids, "c2 must have a ChunkExtraction row"
        assert c1_id not in row_chunk_ids, (
            f"c1 (unclaimed) must have NO ChunkExtraction rows; found in {row_chunk_ids}"
        )

        # --- Chunk statuses ---
        async with async_session_maker() as session:
            chunks = {
                c.id: c
                for c in (
                    await session.execute(select(Chunk).where(Chunk.source_id == source_id))
                )
                .scalars()
                .all()
            }
        assert chunks[c0_id].map_status == MAP_DONE, (
            f"c0 must be MAP_DONE; got {chunks[c0_id].map_status}"
        )
        assert chunks[c2_id].map_status == MAP_DONE, (
            f"c2 must be MAP_DONE; got {chunks[c2_id].map_status}"
        )
        assert chunks[c1_id].map_status == "running", (
            f"c1 must still be 'running' (untouched); got {chunks[c1_id].map_status}"
        )

    run_async(_run())
