"""Tests for LangSmith bootstrap helpers."""

import os

import app.observability.langsmith_setup as langsmith_setup
from app.core.config import Settings
from app.observability.langsmith_setup import (
    configure_langsmith,
    ingest_run_config,
    ingest_tracing_session,
    is_tracing_enabled,
    merge_tracing_config,
)


def test_configure_langsmith_enables_env(monkeypatch):
    monkeypatch.setattr(langsmith_setup, "_initialized", False)
    monkeypatch.delenv("LANGSMITH_TRACING", raising=False)
    monkeypatch.delenv("LANGCHAIN_TRACING_V2", raising=False)
    monkeypatch.delenv("LANGSMITH_API_KEY", raising=False)
    monkeypatch.delenv("LANGCHAIN_PROJECT", raising=False)

    settings = Settings(
        LANGSMITH_TRACING=True,
        LANGSMITH_API_KEY="test-key",
        LANGSMITH_PROJECT="munger-test",
    )
    assert configure_langsmith(settings) is True
    assert is_tracing_enabled() is True
    assert os.environ["LANGSMITH_PROJECT"] == "munger-test"
    assert os.environ["LANGCHAIN_PROJECT"] == "munger-test"
    assert os.environ["LANGCHAIN_CALLBACKS_BACKGROUND"] == "false"


def test_configure_langsmith_disabled_without_key(monkeypatch):
    monkeypatch.setattr(langsmith_setup, "_initialized", False)
    monkeypatch.delenv("LANGCHAIN_TRACING_V2", raising=False)

    settings = Settings(LANGSMITH_TRACING=True, LANGSMITH_API_KEY=None)
    assert configure_langsmith(settings) is False
    assert is_tracing_enabled() is False


def test_ingest_run_config_includes_metadata():
    config = ingest_run_config(
        thread_id="ingest-5-abc",
        source_id=5,
        job_id=12,
        skill_name="ingest",
        recursion_limit=96,
    )
    assert config["configurable"]["thread_id"] == "ingest-5-abc"
    assert config["metadata"]["source_id"] == 5
    assert config["metadata"]["job_id"] == 12
    assert "job:12" in config["tags"]
    assert config["run_name"] == "ingest-source-5"


def test_merge_tracing_config_combines_callbacks():
    base = {"callbacks": ["a"], "run_name": "ingest-source-1"}
    extras = {"callbacks": ["b"]}
    merged = merge_tracing_config(base, extras)
    assert merged["callbacks"] == ["a", "b"]
    assert merged["run_name"] == "ingest-source-1"


def test_ingest_tracing_session_activates_context_when_enabled(monkeypatch):
    # Unified tracing: no manual callback is attached. The session activates a
    # langsmith run-tree context and yields empty extras (nothing to merge into config).
    monkeypatch.setenv("LANGSMITH_TRACING", "true")
    monkeypatch.setenv("LANGCHAIN_TRACING_V2", "true")
    monkeypatch.setenv("LANGSMITH_API_KEY", "test-key")
    settings = Settings(
        LANGSMITH_TRACING=True,
        LANGSMITH_API_KEY="test-key",
        LANGSMITH_PROJECT="munger-test",
    )
    with ingest_tracing_session(settings) as extras:
        assert extras == {}
        assert "callbacks" not in extras


def test_ingest_tracing_session_noop_when_disabled(monkeypatch):
    monkeypatch.setenv("LANGSMITH_TRACING", "false")
    with ingest_tracing_session(Settings(LANGSMITH_TRACING=False)) as extras:
        assert extras == {}
