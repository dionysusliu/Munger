"""Deterministic pipeline benchmark — marker ``bench``.

Drives the REAL ingest graph (LangGraph / service-map mode) over a synthetic
~5 500-token corpus with a ``BenchScriptedLLMService`` (scripted responses,
real DB writes).  Asserts regression bounds and writes a JSON report.

Run with:
    pytest tests/bench/test_bench_pipeline.py -m bench -p no:cacheprovider -v

Script-order rationale (ingest_map_mode=service, window=2, gleanings=0)
------------------------------------------------------------------------
``map_chunks.map_chunks()`` groups chunks into windows of K=2 and calls
``map_window()`` for each window sequentially (concurrency=1 for determinism).

Per window containing chunks [c0, c1]:
  1. chat()          — contextual prefix for c0   → consumes script[i]
  2. chat()          — contextual prefix for c1   → consumes script[i+1]
  3. chat_structured() — extract entities from the window text → script[i+2]

For a trailing window of 1 chunk [c0]:
  1. chat()          — prefix for c0              → script[j]
  2. chat_structured() — extract                  → script[j+1]

``summarize()`` and ``generate_wiki_page()`` are NOT scripted (hardcoded in
ScriptedLLMService) but are tracked in ``BenchScriptedLLMService.stats`` so
``pipeline_step`` can record ``llm_calls`` for those steps.

Wiki-gate note
--------------
``reduce_entities`` initialises every new entity with ``mention_count=1`` and
immediately increments it (``+= 1``), so the minimum possible ``mention_count``
for any extracted entity is 2 (entity appears in exactly 1 chunk).

With ``ingest_wiki_min_mentions=3``:
  • Entities in 1 chunk  → mention_count=2 < 3 → NO wiki page  (singleton gate)
  • Entities in 2+ chunks → mention_count≥3 → wiki page created

We deviate from the plan's suggested value of 2 because threshold=2 would pass
ALL extracted entities (mention_count≥2 always), making the gate unverifiable.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest
from sqlalchemy import func, select

from app.core.config import Settings
from app.core.database import async_session_maker
from app.models.entity import Entity, EntityMention
from app.models.entity_relationship import EntityRelationship
from app.models.ingest_event import IngestEvent
from app.models.source import Source
from app.runtime.context import RuntimeServices
from app.runtime.graphs.ingest import build_ingest_graph
from app.services.chunk_service import ChunkService
from tests.conftest import run_async
from tests.bench.corpus import BenchScriptedLLMService, build_corpus

# ---------------------------------------------------------------------------
# Marker declaration
# ---------------------------------------------------------------------------

pytestmark = pytest.mark.bench

# ---------------------------------------------------------------------------
# Report output path
# ---------------------------------------------------------------------------

REPORTS_DIR = Path(__file__).parent / "reports"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_WIKI_MIN_MENTIONS = 3  # see docstring above for why this is 3 not 2


def _build_services(
    scripts: list, settings: Settings
) -> tuple[BenchScriptedLLMService, RuntimeServices]:
    """Construct RuntimeServices backed by a BenchScriptedLLMService."""
    llm = BenchScriptedLLMService(scripts)
    services = RuntimeServices.from_settings(settings, llm=llm)
    return llm, services


def _group_windows(chunks: list, k: int) -> list[list]:
    """Group chunks (sorted by chunk_index) into consecutive windows of at most k."""
    sorted_chunks = sorted(chunks, key=lambda c: c.chunk_index)
    windows: list[list] = []
    current: list = []
    for chunk in sorted_chunks:
        if not current:
            current.append(chunk)
        elif (
            len(current) < k
            and chunk.chunk_index == current[-1].chunk_index + 1
        ):
            current.append(chunk)
        else:
            windows.append(current)
            current = [chunk]
    if current:
        windows.append(current)
    return windows


# ---------------------------------------------------------------------------
# The benchmark test
# ---------------------------------------------------------------------------

def test_bench_deterministic(create_source):
    """Full pipeline bench with scripted LLM + regression bound assertions."""

    # ------------------------------------------------------------------
    # 1. Build corpus
    # ------------------------------------------------------------------
    corpus = build_corpus(seed=7)

    # ------------------------------------------------------------------
    # 2. Settings (service-map mode, window=2, gleanings=0, serial workers)
    # ------------------------------------------------------------------
    settings = Settings(
        ingest_orchestrator="graph",
        ingest_map_mode="service",
        ingest_max_gleanings=0,
        ingest_extraction_window_chunks=2,
        ingest_comention_min_chunks=2,
        ingest_wiki_min_mentions=_WIKI_MIN_MENTIONS,
        ingest_chunk_worker_concurrency=1,  # serial windows → deterministic script order
    )

    # ------------------------------------------------------------------
    # 3. Create source
    # ------------------------------------------------------------------
    source = create_source(
        status="pending",
        content_text=corpus.text,
        title="Chordal Distributed Systems Survey",
    )

    # ------------------------------------------------------------------
    # 4. Pre-chunk to learn chunk structure before building scripts
    #    (ChunkService with llm=None does not make LLM calls)
    # ------------------------------------------------------------------
    chunk_svc = ChunkService(llm_service=None, settings=settings)
    chunks = run_async(chunk_svc.split_chunks(source.id))
    n_chunks = len(chunks)
    K = settings.ingest_extraction_window_chunks  # 2
    windows = _group_windows(chunks, K)

    assert n_chunks >= 6, f"Expected >= 6 chunks for a meaningful bench, got {n_chunks}"

    # ------------------------------------------------------------------
    # 5. Build scripts
    #    Per window: [prefix_str × len(window), extraction_dict]
    # ------------------------------------------------------------------
    scripts: list = []
    for window in windows:
        run_text = corpus.text[window[0].doc_char_start : window[-1].doc_char_end]
        # Prefix string for each chunk in the window (chat() call)
        for chunk in window:
            scripts.append(f"Context: chunk {chunk.chunk_index + 1} of the document.")
        # Extraction dict for the window (chat_structured() call)
        extraction = corpus.extraction_script_for([run_text])[0]
        scripts.append(extraction)

    # ------------------------------------------------------------------
    # 6. Build services with BenchScriptedLLMService and run the graph
    # ------------------------------------------------------------------
    bench_llm, services = _build_services(scripts, settings)
    graph = build_ingest_graph(services, checkpointer=None)

    run_async(
        graph.ainvoke(
            {"source_id": source.id, "job_id": None},
            config={"configurable": {"thread_id": f"bench-{source.id}"}},
        )
    )

    # ------------------------------------------------------------------
    # 7. Collect DB results
    # ------------------------------------------------------------------
    async def _collect():
        async with async_session_maker() as session:
            src = await session.get(Source, source.id)

            # Unique entity IDs that have a mention for this source
            entity_id_rows = (
                await session.execute(
                    select(EntityMention.entity_id.distinct()).where(
                        EntityMention.source_id == source.id
                    )
                )
            ).scalars().all()
            entity_ids = list(entity_id_rows)

            entities = list(
                (
                    await session.execute(
                        select(Entity).where(Entity.id.in_(entity_ids))
                    )
                )
                .scalars()
                .all()
            )

            co_mention_count = (
                await session.execute(
                    select(func.count()).select_from(EntityRelationship).where(
                        EntityRelationship.source_id == source.id,
                        EntityRelationship.method == "co_mention",
                    )
                )
            ).scalar()

            events = list(
                (
                    await session.execute(
                        select(IngestEvent)
                        .where(
                            IngestEvent.source_id == source.id,
                            IngestEvent.event_type == "pipeline_step_complete",
                        )
                        .order_by(IngestEvent.created_at)
                    )
                )
                .scalars()
                .all()
            )

            return src, entities, co_mention_count, events

    src, entities, co_mention_count, events = run_async(_collect())

    entity_count = len(entities)

    # ------------------------------------------------------------------
    # 8. Assertions — regression bounds
    # ------------------------------------------------------------------

    # Source completed successfully
    assert src.status == "completed", f"Expected status=completed, got {src.status}"
    assert src.content_summary, "summarize_source must set content_summary"

    # Entity count in expected range
    assert 20 <= entity_count <= 60, (
        f"Entity count {entity_count} outside expected range [20, 60]"
    )

    # Co-mention diet: > 0 and well below the all-pairs maximum
    # (min_chunks=2 filter ensures not every entity pair gets a link)
    assert co_mention_count > 0, (
        "Expected at least one co_mention relationship "
        "(popular entities appear together in 2+ windows)"
    )
    max_possible_pairs = entity_count * (entity_count - 1) // 2
    assert co_mention_count <= max_possible_pairs // 2, (
        f"Too many co_mention edges: {co_mention_count} > {max_possible_pairs // 2} "
        f"(more than half of all possible {max_possible_pairs} pairs)"
    )

    # Wiki gate: entities below threshold have no page; entities at/above do
    below_threshold = [e for e in entities if e.mention_count < _WIKI_MIN_MENTIONS]
    above_threshold = [e for e in entities if e.mention_count >= _WIKI_MIN_MENTIONS]

    assert below_threshold, (
        f"Expected at least one entity with mention_count < {_WIKI_MIN_MENTIONS} "
        "(singleton entities appear in only one window)"
    )
    for e in below_threshold:
        assert e.wiki_page_id is None, (
            f"Entity '{e.name}' (mention_count={e.mention_count}) is below the "
            f"wiki threshold ({_WIKI_MIN_MENTIONS}) but has a wiki page"
        )

    assert above_threshold, f"Expected some entities with mention_count >= {_WIKI_MIN_MENTIONS}"
    for e in above_threshold:
        assert e.wiki_page_id is not None, (
            f"Entity '{e.name}' (mention_count={e.mention_count}) meets the "
            f"wiki threshold ({_WIKI_MIN_MENTIONS}) but has no wiki page"
        )

    # Every pipeline_step_complete event must carry duration_ms
    assert events, "Expected pipeline_step_complete events in DB"
    for ev in events:
        assert "duration_ms" in ev.payload, (
            f"Step '{ev.payload.get('step_key')}' missing duration_ms in payload"
        )

    # LLM-heavy steps must have llm_calls >= 1
    step_payloads: dict[str, dict] = {ev.payload["step_key"]: ev.payload for ev in events}
    for step_key in ("map_chunks", "summarize_source", "generate_wiki_pages"):
        assert step_key in step_payloads, f"Step '{step_key}' not found in events"
        llm_calls = step_payloads[step_key].get("metrics", {}).get("llm_calls", 0)
        assert llm_calls >= 1, (
            f"Step '{step_key}' has llm_calls={llm_calls}, expected >= 1. "
            "Check that BenchScriptedLLMService.stats is wired to pipeline_step."
        )

    # Window extraction count: exactly ceil(n_chunks / K)
    expected_extract_calls = math.ceil(n_chunks / K)
    assert bench_llm.extract_calls == expected_extract_calls, (
        f"Expected {expected_extract_calls} extraction calls "
        f"(ceil({n_chunks}/{K})), got {bench_llm.extract_calls}"
    )

    # ------------------------------------------------------------------
    # 9. Write JSON report
    # ------------------------------------------------------------------
    REPORTS_DIR.mkdir(exist_ok=True)

    step_report: dict[str, dict] = {}
    for ev in events:
        key = ev.payload["step_key"]
        metrics = ev.payload.get("metrics", {})
        step_report[key] = {
            "duration_ms": ev.payload.get("duration_ms", 0),
            "llm_calls": metrics.get("llm_calls", 0),
            "llm_ms": metrics.get("llm_ms", 0),
        }

    report = {
        "corpus_chars": len(corpus.text),
        "chunks": n_chunks,
        "windows": len(windows),
        "entity_count": entity_count,
        "co_mention_count": co_mention_count,
        "wiki_pages": sum(1 for e in entities if e.wiki_page_id is not None),
        "singleton_count": len(below_threshold),
        "extract_calls": bench_llm.extract_calls,
        "total_llm_calls": bench_llm.stats["calls"],
        "steps": step_report,
    }

    report_path = REPORTS_DIR / "bench-deterministic.json"
    report_path.write_text(json.dumps(report, indent=2))

    # Print summary for CI log visibility
    print(
        f"\n[bench] entities={entity_count}  co_mention={co_mention_count}  "
        f"chunks={n_chunks}  windows={len(windows)}  "
        f"extract_calls={bench_llm.extract_calls}  "
        f"total_llm_calls={bench_llm.stats['calls']}"
    )
    print(f"[bench] Report → {report_path}")
