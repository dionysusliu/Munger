"""Live pipeline benchmark against the REAL OpenRouter provider — markers ``bench`` + ``live_llm``.

Drives the SAME synthetic corpus as ``test_bench_pipeline.py`` (seed=7, ~5 500
tokens, 30 embedded entities) through the REAL ingest graph with a REAL
``LLMService`` (OpenRouter), records the same per-step report JSON, and — when
``tests/bench/baselines/baseline.json`` exists — compares per-step
``duration_ms`` / ``llm_calls`` against it, emitting ``warnings.warn`` (never a
failure) on regressions.

Run it explicitly (costs real money — the corpus is small but wiki-page
generation makes ~100+ chat calls):

    OPENROUTER_API_KEY=sk-or-... \
    TEST_DATABASE_URL=postgresql+psycopg://munger_app:Munger.App.2026@localhost:5432/munger_test \
    .venv/bin/python -m pytest tests/bench/test_bench_live.py -o addopts="" -m "bench and live_llm" -v

Optional overrides: LIVE_CHAT_MODEL (default deepseek/deepseek-v4-flash),
LIVE_EMBED_MODEL (default qwen/qwen3-embedding-8b — must yield 768 dims).

Default behavior: marked ``bench`` so pytest.ini's
``addopts = -m "not integration and not bench"`` DESELECTS it from the normal
suite; and it skips cleanly when OPENROUTER_API_KEY is unset. Transient
external failures (auth/rate-limit/connection/timeout) skip rather than fail.

Assertions are the provider-independent SUBSET of the deterministic tier's
bounds: pipeline-logic invariants (wiki gate, co-mention diet relative to the
extracted entity count, step telemetry presence) hold for ANY provider, while
exact entity counts / extraction-call counts are scripted-only and are NOT
asserted here (entity-count bound is wide: >= 5).
"""

from __future__ import annotations

import json
import os
import subprocess
import time
import warnings
from datetime import datetime, timezone
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
from app.schemas.extraction import ExtractionResult
from app.services.chunk_service import ChunkService
from app.services.llm_service import LLMService
from tests.bench.corpus import build_corpus
from tests.bench.test_bench_pipeline import _WIKI_MIN_MENTIONS, _group_windows
from tests.conftest import run_async

# ---------------------------------------------------------------------------
# Marker declaration — bench keeps it out of the default run (addopts),
# live_llm flags the real-provider dependency.
# ---------------------------------------------------------------------------

pytestmark = [pytest.mark.bench, pytest.mark.live_llm]

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

REPORTS_DIR = Path(__file__).parent / "reports"
BASELINE_PATH = Path(__file__).parent / "baselines" / "baseline.json"

# ---------------------------------------------------------------------------
# Live-provider plumbing — mirrors tests/live/test_live_llm.py
# ---------------------------------------------------------------------------

_EXTERNAL_MARKERS = (
    "api key", "unauthorized", "forbidden", "rate limit", "rate-limit", "timeout", "timed out",
    "connection", "openrouter", "http 4", "http 5", "temporar", "quota", "insufficient", "overloaded",
)


def _skip_if_external(exc: Exception) -> None:
    """Skip (not fail) on a transient/external provider error; re-raise genuine code bugs."""
    msg = str(exc).lower()
    if any(m in msg for m in _EXTERNAL_MARKERS):
        pytest.skip(f"blocked external dependency: {exc}")
    raise exc


def _live_settings() -> Settings:
    key = os.getenv("OPENROUTER_API_KEY")
    if not key:
        pytest.skip("OPENROUTER_API_KEY not set — live LLM tests are opt-in")
    # Build our own Settings (conftest forces get_settings() to ollama; we must not use it here).
    # Provider block matches tests/live/test_live_llm.py; ingest block matches
    # tests/bench/test_bench_pipeline.py EXACTLY so the only A/B variable is the provider.
    return Settings(
        LLM_DEFAULT_PROVIDER="openrouter",
        OPENROUTER_API_KEY=key,
        LLM_DEFAULT_MODEL=os.getenv("LIVE_CHAT_MODEL", "deepseek/deepseek-v4-flash"),
        LLM_EMBEDDING_MODEL=os.getenv("LIVE_EMBED_MODEL", "qwen/qwen3-embedding-8b"),
        LLM_EMBEDDING_DIMENSIONS=768,
        ingest_orchestrator="graph",
        ingest_map_mode="service",
        ingest_max_gleanings=0,
        ingest_extraction_window_chunks=2,
        ingest_comention_min_chunks=2,
        ingest_wiki_min_mentions=_WIKI_MIN_MENTIONS,
        ingest_chunk_worker_concurrency=1,
    )


class LiveBenchLLMService(LLMService):
    """Real LLMService + an ``extract_calls`` counter for report-shape parity.

    The real service already maintains ``stats`` (calls/ms) which
    ``pipeline_step`` snapshots per step; we only add the window-extraction
    counter the deterministic report carries (counted as ``chat_structured``
    requests whose response model is ``ExtractionResult``).
    """

    def __init__(self, settings: Settings):
        super().__init__(settings)
        self.extract_calls: int = 0

    async def chat_structured(self, messages: list[dict], response_model: type, **kwargs):
        if response_model is ExtractionResult:
            self.extract_calls += 1
        return await super().chat_structured(messages, response_model, **kwargs)


@pytest.fixture
def live():
    settings = _live_settings()
    # Realtime observability: when OTEL_EXPORTER_OTLP_ENDPOINT is set (e.g. the
    # compose LGTM stack at http://localhost:4318), pipeline_step spans and every
    # OpenRouter httpx call stream to Tempo live — progress is watchable via
    # REST mid-run instead of a black-box wait. No-op when the env is unset.
    from app.observability.otel_setup import setup_otel

    setup_otel("munger-bench-live")
    return settings, LiveBenchLLMService(settings)


# ---------------------------------------------------------------------------
# Baseline comparison — warn-only, never fails the test
# ---------------------------------------------------------------------------

class BenchBaselineWarning(UserWarning):
    """A live-bench step regressed versus tests/bench/baselines/baseline.json."""


def compare_to_baseline(report: dict, baseline_path: Path = BASELINE_PATH) -> list[str]:
    """Return regression messages for *report* versus the committed baseline.

    Policy (warn-only):
      * duration_ms  — warn when current > 2x baseline, for steps whose baseline
        duration is >= 100 ms (sub-100 ms steps are scheduler noise);
      * llm_calls    — warn when current > 1.5x baseline (i.e. a >50% increase),
        for steps with a non-zero baseline call count.

    Steps present in only one of the two reports are ignored. Returns [] when
    no baseline file exists.
    """
    if not baseline_path.exists():
        return []
    baseline = json.loads(baseline_path.read_text())
    messages: list[str] = []
    for step_key, base in baseline.get("steps", {}).items():
        cur = report.get("steps", {}).get(step_key)
        if cur is None:
            continue
        base_ms = base.get("duration_ms", 0)
        cur_ms = cur.get("duration_ms", 0)
        if base_ms >= 100 and cur_ms > 2 * base_ms:
            messages.append(
                f"{step_key}: duration_ms {cur_ms} > 2x baseline {base_ms}"
            )
        base_calls = base.get("llm_calls", 0)
        cur_calls = cur.get("llm_calls", 0)
        if base_calls > 0 and cur_calls > 1.5 * base_calls:
            messages.append(
                f"{step_key}: llm_calls {cur_calls} > 1.5x baseline {base_calls} (+50% threshold)"
            )
    return messages


def _git_sha() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent,
            check=False,
        )
        sha = out.stdout.strip()
    except OSError:
        sha = ""
    return sha or "nogit"


# ---------------------------------------------------------------------------
# The live benchmark test
# ---------------------------------------------------------------------------

def test_bench_live(live, create_source):
    """Same corpus + same graph as the deterministic tier, real provider."""
    settings, llm = live

    # ------------------------------------------------------------------
    # 1. Corpus + source (identical to deterministic tier)
    # ------------------------------------------------------------------
    corpus = build_corpus(seed=7)
    source = create_source(
        status="pending",
        content_text=corpus.text,
        title="Chordal Distributed Systems Survey",
    )

    # ------------------------------------------------------------------
    # 2. Pre-chunk only to learn window structure for the report
    #    (ChunkService with llm=None makes no LLM calls; the graph's
    #    chunk_document step deletes + re-chunks idempotently)
    # ------------------------------------------------------------------
    chunk_svc = ChunkService(llm_service=None, settings=settings)
    chunks = run_async(chunk_svc.split_chunks(source.id))
    n_chunks = len(chunks)
    windows = _group_windows(chunks, settings.ingest_extraction_window_chunks)

    # ------------------------------------------------------------------
    # 3. Run the REAL graph with the REAL provider
    # ------------------------------------------------------------------
    services = RuntimeServices.from_settings(settings, llm=llm)
    graph = build_ingest_graph(services, checkpointer=None)

    t0 = time.perf_counter()
    try:
        run_async(
            graph.ainvoke(
                {"source_id": source.id, "job_id": None},
                config={"configurable": {"thread_id": f"bench-live-{source.id}"}},
            )
        )
    except Exception as exc:  # noqa: BLE001
        _skip_if_external(exc)
    wall_ms = int((time.perf_counter() - t0) * 1000)

    # ------------------------------------------------------------------
    # 4. Collect DB results (same queries as deterministic tier)
    # ------------------------------------------------------------------
    async def _collect():
        async with async_session_maker() as session:
            src = await session.get(Source, source.id)

            entity_ids = (
                await session.execute(
                    select(EntityMention.entity_id.distinct()).where(
                        EntityMention.source_id == source.id
                    )
                )
            ).scalars().all()

            entities = list(
                (
                    await session.execute(
                        select(Entity).where(Entity.id.in_(list(entity_ids)))
                    )
                ).scalars().all()
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
                ).scalars().all()
            )

            return src, entities, co_mention_count, events

    src, entities, co_mention_count, events = run_async(_collect())
    entity_count = len(entities)

    # ------------------------------------------------------------------
    # 5. Assertions — provider-independent structural bounds only
    # ------------------------------------------------------------------

    # Pipeline completed against the real provider
    assert src.status == "completed", f"Expected status=completed, got {src.status}"
    assert src.content_summary, "summarize_source must set content_summary"

    # WIDE entity bound — real-LLM extraction varies run to run
    assert entity_count >= 5, (
        f"Entity count {entity_count} < 5 — real extraction should find a "
        "meaningful fraction of the 30 embedded entities"
    )

    # Co-mention diet: the min_chunks=2 filter must keep the edge count linear-ish
    # in the entity count, never the all-pairs blowup.
    assert co_mention_count <= entity_count * 3, (
        f"Too many co_mention edges: {co_mention_count} > 3x entities ({entity_count})"
    )

    # Wiki gate: entities below the mention threshold must NOT have a wiki page.
    # (The inverse — above-threshold entities DO get pages — is asserted only in
    # the deterministic tier: a transient provider error on one page-generation
    # call is swallowed by the pipeline and must not flake the live bench.)
    below_threshold = [e for e in entities if e.mention_count < _WIKI_MIN_MENTIONS]
    for e in below_threshold:
        assert e.wiki_page_id is None, (
            f"Entity '{e.name}' (mention_count={e.mention_count}) is below the "
            f"wiki threshold ({_WIKI_MIN_MENTIONS}) but has a wiki page"
        )

    # Every pipeline_step_complete event must carry duration_ms
    assert events, "Expected pipeline_step_complete events in DB"
    for ev in events:
        assert "duration_ms" in ev.payload, (
            f"Step '{ev.payload.get('step_key')}' missing duration_ms in payload"
        )

    # LLM-heavy steps must have llm_calls >= 1 (real LLMService.stats wiring)
    step_payloads: dict[str, dict] = {ev.payload["step_key"]: ev.payload for ev in events}
    for step_key in ("map_chunks", "summarize_source", "generate_wiki_pages"):
        assert step_key in step_payloads, f"Step '{step_key}' not found in events"
        llm_calls = step_payloads[step_key].get("metrics", {}).get("llm_calls", 0)
        assert llm_calls >= 1, (
            f"Step '{step_key}' has llm_calls={llm_calls}, expected >= 1. "
            "Check that LLMService.stats is wired to pipeline_step."
        )

    # ------------------------------------------------------------------
    # 6. Write JSON report — same shape as the deterministic tier
    #    (+ total_llm_ms and a meta provenance block)
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
        "extract_calls": llm.extract_calls,
        "total_llm_calls": llm.stats["calls"],
        "total_llm_ms": llm.stats["ms"],
        "steps": step_report,
        "meta": {
            "tier": "live",
            "git_sha": _git_sha(),
            "chat_model": settings.default_llm_model,
            "embed_model": settings.embedding_model,
            "wall_ms": wall_ms,
            "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        },
    }

    report_path = REPORTS_DIR / f"bench-live-{_git_sha()}.json"
    report_path.write_text(json.dumps(report, indent=2))

    # ------------------------------------------------------------------
    # 7. Baseline A/B — warn (never fail) on regressions
    # ------------------------------------------------------------------
    regressions = compare_to_baseline(report)
    for msg in regressions:
        warnings.warn(BenchBaselineWarning(msg), stacklevel=2)

    # Print summary for log visibility
    print(
        f"\n[bench-live] entities={entity_count}  co_mention={co_mention_count}  "
        f"chunks={n_chunks}  windows={len(windows)}  "
        f"extract_calls={llm.extract_calls}  total_llm_calls={llm.stats['calls']}  "
        f"total_llm_ms={llm.stats['ms']}  wall_ms={wall_ms}"
    )
    print(f"[bench-live] Report → {report_path}")
    if BASELINE_PATH.exists():
        print(
            f"[bench-live] Baseline comparison: {len(regressions)} regression(s) "
            f"vs {BASELINE_PATH.name}"
        )
    else:
        print("[bench-live] No baseline.json — comparison skipped")
