"""Entity salience selection — filter unimportant entities before expensive work.

Pure, side-effect-free so it can be unit-tested without a database. A node computes
the per-source meta (mention count + distinct-chunk spread) and calls this.
"""

from __future__ import annotations

from typing import Iterable, Protocol


class _EntityMeta(Protocol):
    id: int
    mentions: int
    spread: int


def _score(mentions: int, spread: int) -> float:
    # Mentions drive the score; chunk spread breaks ties and rewards entities that
    # recur across the document (more central) over ones clustered in one place.
    return mentions + 0.5 * spread


def select_salient_entities(
    meta: Iterable[_EntityMeta],
    *,
    min_mentions: int,
    top_k: int,
) -> set[int]:
    """Return the ids of salient entities.

    Keep entities with at least ``min_mentions`` mentions, then take the top
    ``top_k`` by score (mentions + 0.5 * chunk-spread). Ties break on lower id for
    determinism.
    """
    scored: list[tuple[float, int]] = []
    for e in meta:
        if e.mentions < min_mentions:
            continue
        scored.append((_score(e.mentions, e.spread), e.id))
    scored.sort(key=lambda x: (-x[0], x[1]))
    return {eid for _s, eid in scored[:top_k]}
