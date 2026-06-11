"""Characterize the intake subgraph: register_source, parse_document, hash_dedup.

Key findings (confirmed by reading nodes_intake.py):
- n_parse (lines 56-58): short-circuits if content_text is already set; does NOT recompute
  content_hash from content_text.
- n_hash_dedup (line 97): keys on Source.content_hash directly from the DB column; compares
  against other rows with status == "completed".
- conftest.create_source generates content_hash=f"hash-{title.lower().replace(' ', '-')}",
  so two sources with different titles get different hashes by default.
"""

from sqlalchemy import update

from app.core.database import async_session_maker
from app.models.source import Source
from app.runtime.graphs.intake import build_intake_subgraph
from tests.conftest import run_async
from tests.fixtures.ingest_fixtures import scripted_services, two_entity_scripts


def _run_intake(source_id: int):
    """Invoke the compiled intake subgraph for the given source_id."""
    services = scripted_services(two_entity_scripts())
    sub = build_intake_subgraph(services)

    async def _inner():
        return await sub.ainvoke(
            {"source_id": source_id, "job_id": None},
            config={"configurable": {"thread_id": f"intake-{source_id}"}},
        )

    return run_async(_inner())


def test_register_and_parse_caches_text_and_marks_not_duplicate(create_source):
    """A pending source with pre-populated content_text completes intake as non-duplicate.

    n_register sets status=extracting; n_parse preserves existing content_text;
    n_hash_dedup finds no completed source with the same hash → is_duplicate=False.
    """
    source = create_source(status="pending", content_text="Some content for parsing.")
    state = _run_intake(source.id)

    async def _src():
        async with async_session_maker() as session:
            return await session.get(Source, source.id)

    src = run_async(_src())
    assert src.content_text and len(src.content_text) > 0, (
        "parse_document must preserve content_text in the DB"
    )
    # register_source sets status=extracting; parse + (non-duplicate) dedup leave it unchanged.
    assert src.status == "extracting", "register_source must set status=extracting"
    assert state.get("is_duplicate") is False


def test_hash_dedup_flags_second_identical_source(create_source):
    """A second source sharing content_hash with a completed source is flagged as duplicate.

    n_parse does NOT recompute content_hash from content_text (nodes_intake.py:56-58).
    n_hash_dedup keys on Source.content_hash (nodes_intake.py:97).
    create_source derives hashes from the title, so sources with different titles get
    different hashes by default; we align them explicitly with a DB UPDATE before intake.
    """
    SHARED_HASH = "hash-identical-body"
    first = create_source(
        title="Original",
        status="completed",
        content_text="Identical body for dedup test.",
    )
    second = create_source(
        title="Duplicate",
        status="pending",
        content_text="Identical body for dedup test.",
    )

    # Set both rows to the same content_hash so n_hash_dedup can match them.
    async def _set_hashes():
        async with async_session_maker() as session:
            await session.execute(
                update(Source)
                .where(Source.id.in_([first.id, second.id]))
                .values(content_hash=SHARED_HASH)
            )
            await session.commit()

    run_async(_set_hashes())

    state = _run_intake(second.id)
    assert state.get("is_duplicate") is True, (
        "hash_dedup must flag the second source as a duplicate of the first"
    )
    assert state.get("duplicate_of_source_id") == first.id
