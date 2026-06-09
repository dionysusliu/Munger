import os
import time

import httpx
import pytest

pytestmark = [pytest.mark.integration, pytest.mark.provider]

BACKEND_BASE_URL = os.getenv("BACKEND_BASE_URL", "http://localhost:18000")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "qwen/qwen3.6-plus")


def _require_provider_or_skip() -> None:
    if not os.getenv("OPENROUTER_API_KEY"):
        pytest.skip("blocked external dependency: OPENROUTER_API_KEY not set")

    response = httpx.post(
        f"{BACKEND_BASE_URL}/api/config/test-model",
        params={"provider": "openrouter", "model": OPENROUTER_MODEL},
        timeout=60.0,
    )
    response.raise_for_status()
    payload = response.json()

    if payload.get("status") == "connected":
        return

    error = payload.get("error", "OpenRouter unavailable")
    external_markers = (
        "api key",
        "unauthorized",
        "rate limit",
        "timeout",
        "connection",
        "openrouter api error",
        "http 4",
        "http 5",
        "temporar",
    )
    if any(marker in error.lower() for marker in external_markers):
        pytest.skip(f"blocked external dependency: {error}")

    pytest.fail(f"provider check failed due to backend issue: {payload}")


def test_openrouter_schema_check():
    _require_provider_or_skip()

    response = httpx.post(
        f"{BACKEND_BASE_URL}/api/config/test-model",
        params={"provider": "openrouter", "model": OPENROUTER_MODEL},
        timeout=60.0,
    )
    response.raise_for_status()
    payload = response.json()

    assert payload["provider"] == "openrouter"
    assert payload["model"] == OPENROUTER_MODEL
    assert payload["status"] == "connected"
    assert "response_preview" in payload


def test_upload_ingest_entity_wiki_generation_e2e():
    _require_provider_or_skip()

    before_entities = httpx.get(f"{BACKEND_BASE_URL}/api/entities", timeout=20.0).json()["total"]
    before_pages = httpx.get(f"{BACKEND_BASE_URL}/api/wiki", timeout=20.0).json()["total"]

    unique_suffix = str(int(time.time()))
    title = f"Provider E2E Source {unique_suffix}"
    content = (
        f"Run ID: {unique_suffix}. "
        "Alice Arbor founded Atlas Dynamics."
    )

    upload = httpx.post(
        f"{BACKEND_BASE_URL}/api/sources/upload",
        files={"file": ("provider-e2e.txt", content.encode("utf-8"), "text/plain")},
        data={"title": title},
        timeout=30.0,
    )
    upload.raise_for_status()
    source_id = upload.json()["id"]

    trigger = httpx.post(f"{BACKEND_BASE_URL}/api/sources/{source_id}/ingest", timeout=30.0)
    trigger.raise_for_status()

    deadline = time.time() + 600
    last_status = None
    while time.time() < deadline:
        status_response = httpx.get(f"{BACKEND_BASE_URL}/api/sources/{source_id}/status", timeout=20.0)
        status_response.raise_for_status()
        status_payload = status_response.json()
        last_status = status_payload["status"]
        if last_status == "completed":
            break
        if last_status == "failed":
            error_message = status_payload.get("error_message", "")
            if "OpenRouter" in error_message or "API key" in error_message or "HTTP 4" in error_message:
                pytest.skip(f"blocked external dependency: {error_message}")
            pytest.fail(f"ingest failed: {status_payload}")
        time.sleep(2)
    else:
        pytest.fail(f"ingest did not complete in time; last status={last_status}")

    after_entities = httpx.get(f"{BACKEND_BASE_URL}/api/entities", timeout=20.0).json()["total"]
    after_pages = httpx.get(f"{BACKEND_BASE_URL}/api/wiki", timeout=20.0).json()["total"]
    source_pages = httpx.get(f"{BACKEND_BASE_URL}/api/wiki", params={"search": title}, timeout=20.0).json()

    # Entity totals may not increase when find_or_create reuses existing entities.
    assert after_pages > before_pages
    assert source_pages["total"] >= 1

    entity_search = httpx.get(
        f"{BACKEND_BASE_URL}/api/entities",
        params={"search": "Atlas Dynamics"},
        timeout=20.0,
    )
    entity_search.raise_for_status()
    entity_payload = entity_search.json()
    assert entity_payload["total"] >= 1, "expected Atlas Dynamics entity after ingest"

    entity_id = entity_payload["items"][0]["id"]
    mentions = httpx.get(
        f"{BACKEND_BASE_URL}/api/entities/{entity_id}/mentions",
        timeout=20.0,
    )
    mentions.raise_for_status()
    mention_payload = mentions.json()
    assert any(
        mention.get("source_id") == source_id for mention in mention_payload.get("mentions", [])
    ), "expected entity mention linked to ingested source"
