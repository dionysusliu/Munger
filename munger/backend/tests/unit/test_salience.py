"""Salience gate: keep only important entities before the expensive wiki/link work."""

from types import SimpleNamespace

from app.services.salience import select_salient_entities


def _e(id, mentions, spread=1, name="Entity"):
    return SimpleNamespace(id=id, mentions=mentions, spread=spread, name=name)


def test_drops_entities_below_min_mentions():
    meta = [_e(1, 5), _e(2, 1), _e(3, 2)]
    selected = select_salient_entities(meta, min_mentions=2, top_k=100)
    assert selected == {1, 3}


def test_caps_to_top_k_by_score():
    meta = [_e(i, mentions=i) for i in range(1, 11)]  # mentions 1..10
    selected = select_salient_entities(meta, min_mentions=2, top_k=3)
    # top 3 by mention count: ids 10, 9, 8
    assert selected == {8, 9, 10}


def test_chunk_spread_boosts_score():
    # Same mention count, but id 2 spans more chunks → ranks higher.
    meta = [_e(1, mentions=4, spread=1), _e(2, mentions=4, spread=10)]
    selected = select_salient_entities(meta, min_mentions=2, top_k=1)
    assert selected == {2}


def test_empty():
    assert select_salient_entities([], min_mentions=2, top_k=10) == set()
