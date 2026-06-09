"""Citation excerpt should be a readable sentence window, not the bare entity span."""

from types import SimpleNamespace

from app.runtime.graphs.nodes.nodes_cognify import _excerpt_from_mention


def _mention(char_start=None, char_end=None, context=None):
    return SimpleNamespace(char_start=char_start, char_end=char_end, context=context)


def test_expands_bare_span_to_full_sentence():
    text = "First sentence here. The last packet from the source is delayed badly. Third one."
    i = text.index("packet")
    result = _excerpt_from_mention(text, _mention(i, i + len("packet")))
    # Must return the surrounding sentence, not just "packet".
    assert result == "The last packet from the source is delayed badly."


def test_collapses_mangled_whitespace():
    text = "Alpha here. The  last      packet   is   fine now. Beta."
    i = text.index("packet")
    result = _excerpt_from_mention(text, _mention(i, i + len("packet")))
    assert "  " not in result
    assert "packet" in result


def test_null_offsets_fall_back_to_context():
    result = _excerpt_from_mention("ignored source", _mention(None, None, "some   context  here"))
    assert result == "some context here"


def test_out_of_range_offsets_fall_back_to_context():
    result = _excerpt_from_mention("short text", _mention(99999, 100005, "ctx fallback"))
    assert result == "ctx fallback"


def test_inverted_offsets_fall_back():
    result = _excerpt_from_mention("short text", _mention(5, 2, "ctx"))
    assert result == "ctx"


def test_empty_when_no_offsets_no_context():
    assert _excerpt_from_mention("x", _mention(None, None, None)) == ""
