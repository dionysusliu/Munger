"""LangSmith tracing bootstrap for ingest pipeline and custom LLM calls."""

from __future__ import annotations

import functools
import logging
import os
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Any, TypeVar

from app.core.config import Settings

logger = logging.getLogger(__name__)

_initialized = False
F = TypeVar("F", bound=Callable[..., Any])

# Graph nodes registered on LangGraph StateGraph (not conditional-edge routers).
INGEST_GRAPH_NODE_NAMES: frozenset[str] = frozenset(
    {
        "n_register",
        "n_parse",
        "n_hash_dedup",
        "n_skip",
        "n_chunk",
        "n_process_chunk",
        "n_map",
        "n_map_gate",
        "n_reduce",
        "n_link",
        "n_summarize",
        "n_wiki",
        "n_finalize",
    }
)


def configure_langsmith(settings: Settings | None = None) -> bool:
    """Apply LangSmith env vars once at process startup. Returns True if active."""
    global _initialized
    if _initialized:
        return is_tracing_enabled()

    if settings is None:
        from app.core.config import get_settings

        settings = get_settings()

    enabled = bool(settings.langsmith_tracing and settings.langsmith_api_key)
    if enabled:
        os.environ["LANGSMITH_TRACING"] = "true"
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGSMITH_API_KEY"] = settings.langsmith_api_key or ""
        os.environ["LANGSMITH_PROJECT"] = settings.langsmith_project
        # Legacy LangChain SDK compat + explicit project routing.
        os.environ["LANGCHAIN_PROJECT"] = settings.langsmith_project
        # Flush traces before ingest jobs exit (worker is job-scoped, not long-poll).
        os.environ["LANGCHAIN_CALLBACKS_BACKGROUND"] = "false"
        if settings.langsmith_endpoint:
            os.environ["LANGSMITH_ENDPOINT"] = settings.langsmith_endpoint
        logger.info(
            "LangSmith tracing enabled (project=%s)",
            settings.langsmith_project,
        )
    else:
        os.environ.pop("LANGCHAIN_TRACING_V2", None)
        os.environ.pop("LANGCHAIN_PROJECT", None)
        if not settings.langsmith_tracing:
            logger.info("LangSmith tracing disabled (LANGSMITH_TRACING=false)")
        elif not settings.langsmith_api_key:
            logger.warning(
                "LangSmith tracing requested but LANGSMITH_API_KEY is unset; traces will not export"
            )

    _initialized = True
    return enabled


def is_tracing_enabled() -> bool:
    return (
        os.environ.get("LANGSMITH_TRACING", "").lower() == "true"
        and bool(os.environ.get("LANGSMITH_API_KEY"))
        and os.environ.get("LANGCHAIN_TRACING_V2", "").lower() == "true"
    )


def ingest_run_config(
    *,
    thread_id: str,
    source_id: int,
    job_id: int | None,
    skill_name: str = "ingest",
    recursion_limit: int,
) -> dict[str, Any]:
    """RunnableConfig for LangGraph ingest runs with LangSmith metadata."""
    tags = ["ingest", f"source:{source_id}"]
    if job_id is not None:
        tags.append(f"job:{job_id}")

    return {
        "configurable": {"thread_id": thread_id},
        "recursion_limit": recursion_limit,
        "run_name": f"ingest-source-{source_id}",
        "tags": tags,
        "metadata": {
            "source_id": source_id,
            "job_id": job_id,
            "thread_id": thread_id,
            "skill_name": skill_name,
        },
    }


def merge_tracing_config(base: dict[str, Any], extras: dict[str, Any]) -> dict[str, Any]:
    """Merge tracing callbacks into a RunnableConfig without dropping existing keys."""
    if not extras:
        return base
    merged = {**base, **extras}
    base_callbacks = base.get("callbacks") or []
    extra_callbacks = extras.get("callbacks") or []
    if base_callbacks or extra_callbacks:
        merged["callbacks"] = [*base_callbacks, *extra_callbacks]
    return merged


@contextmanager
def ingest_tracing_session(settings: Settings | None = None) -> Iterator[dict[str, Any]]:
    """Attach LangChainTracer callbacks for one ingest graph run.

    Project routing uses LANGSMITH_PROJECT / LANGCHAIN_PROJECT from configure_langsmith().
    LangGraph creates the nested node tree; avoid duplicate @traceable wrappers on nodes.
    """
    if settings is None:
        from app.core.config import get_settings

        settings = get_settings()

    extras: dict[str, Any] = {}
    if not is_tracing_enabled():
        yield extras
        return

    try:
        from langchain_core.tracers.langchain import LangChainTracer
    except ImportError as exc:
        logger.warning("LangSmith tracing dependencies unavailable: %s", exc)
        yield extras
        return

    extras["callbacks"] = [LangChainTracer(project_name=settings.langsmith_project)]
    yield extras


def trace_graph_node(*, name: str, run_type: str = "chain") -> Callable[[F], F]:
    """Decorator for LangGraph node functions (custom Python, not LangChain runnables)."""

    def decorator(func: F) -> F:
        traced: F | None = None

        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            nonlocal traced
            if not is_tracing_enabled():
                return await func(*args, **kwargs)
            if traced is None:
                try:
                    from langsmith import traceable

                    traced = traceable(name=name, run_type=run_type)(func)  # type: ignore[assignment]
                except ImportError:
                    logger.warning("langsmith package missing; cannot trace node %s", name)
                    return await func(*args, **kwargs)
            return await traced(*args, **kwargs)  # type: ignore[misc]

        return async_wrapper  # type: ignore[return-value]

    return decorator


def wrap_graph_nodes(nodes: dict[str, Any], *, names: frozenset[str] | None = None) -> dict[str, Any]:
    """Apply trace_graph_node to selected graph node callables."""
    selected = names or INGEST_GRAPH_NODE_NAMES
    wrapped = dict(nodes)
    for key in selected:
        fn = wrapped.get(key)
        if callable(fn):
            wrapped[key] = trace_graph_node(name=key)(fn)
    return wrapped


def trace_llm(*, name: str, run_type: str = "llm") -> Callable[[F], F]:
    """Decorator for custom httpx LLM calls; no-op when tracing is disabled."""

    def decorator(func: F) -> F:
        traced: F | None = None

        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            nonlocal traced
            if not is_tracing_enabled():
                return await func(*args, **kwargs)
            if traced is None:
                try:
                    from langsmith import traceable

                    traced = traceable(name=name, run_type=run_type)(func)  # type: ignore[assignment]
                except ImportError:
                    logger.warning("langsmith package missing; cannot trace %s", name)
                    return await func(*args, **kwargs)
            return await traced(*args, **kwargs)  # type: ignore[misc]

        return async_wrapper  # type: ignore[return-value]

    return decorator
