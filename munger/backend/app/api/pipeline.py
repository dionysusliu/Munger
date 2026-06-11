"""Pipeline topology endpoint — the server-driven step registry for the observability UI."""

from fastapi import APIRouter

from app.runtime.pipeline_events import GRAPH_STEP_ORDER, STEP_LABELS

router = APIRouter()

# First three steps are the intake subgraph; the rest are cognify. map_chunks fans out.
_INTAKE = {"register_source", "parse_document", "hash_dedup"}


@router.get("/topology")
async def topology_endpoint():
    stages = [
        {
            "key": key,
            "label": STEP_LABELS.get(key, key),
            "index": i,
            "group": "intake" if key in _INTAKE else "cognify",
            "fan_out": key == "map_chunks",
        }
        for i, key in enumerate(GRAPH_STEP_ORDER)
    ]
    return {"stages": stages, "total": len(stages)}
