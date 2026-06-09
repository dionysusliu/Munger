"""LangChain tools for Munger runtime."""

from app.runtime.pipeline_events import INGEST_TOOL_ORDER

__all__ = ["INGEST_TOOL_ORDER", "build_ingest_tools"]


def build_ingest_tools(*args, **kwargs):
    from app.runtime.tools.ingest_tools import build_ingest_tools as _build

    return _build(*args, **kwargs)
