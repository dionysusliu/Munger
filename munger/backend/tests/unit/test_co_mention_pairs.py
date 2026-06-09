"""Co-mention linking must threshold by co-occurrence and cap per-entity degree."""

from app.services.linking_service import LinkingService


def _chunk_map(chunks: dict[int, set[int]]):
    """Build (chunk_entities, entity_chunks) from {chunk_id: {entity_ids}}."""
    entity_chunks: dict[int, set[int]] = {}
    for cid, ents in chunks.items():
        for e in ents:
            entity_chunks.setdefault(e, set()).add(cid)
    return chunks, entity_chunks


def test_drops_pairs_below_min_cooccurrence():
    # A&B share chunks 1,2 (=2); A&C share only chunk 3 (=1).
    ce, ec = _chunk_map({1: {10, 11}, 2: {10, 11}, 3: {10, 12}})
    pairs = LinkingService._co_mention_pairs(ce, ec, min_cooccur=2, max_degree=50)
    assert (10, 11) in pairs
    assert (10, 12) not in pairs
    # weight + supporting chunk recorded
    weight, chunk = pairs[(10, 11)]
    assert weight == 2
    assert chunk == 1


def test_single_cooccurrence_kept_when_threshold_is_one():
    ce, ec = _chunk_map({1: {10, 11}})
    pairs = LinkingService._co_mention_pairs(ce, ec, min_cooccur=1, max_degree=50)
    assert (10, 11) in pairs


def test_caps_out_degree_per_entity():
    # Hub entity 1 co-occurs (2 shared chunks each) with 20 partners.
    chunks: dict[int, set[int]] = {}
    cid = 0
    for partner in range(100, 120):
        chunks[cid := cid + 1] = {1, partner}
        chunks[cid := cid + 1] = {1, partner}
    ce, ec = _chunk_map(chunks)
    pairs = LinkingService._co_mention_pairs(ce, ec, min_cooccur=2, max_degree=5)
    hub_edges = [p for p in pairs if 1 in p]
    assert len(hub_edges) <= 5


def test_empty_input():
    assert LinkingService._co_mention_pairs({}, {}, min_cooccur=2, max_degree=5) == {}
