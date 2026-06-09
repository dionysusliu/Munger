"""Extraction hygiene: drop obvious non-entities (numbers, trace labels) at the source."""

import pytest

from app.services.entity_hygiene import is_low_value_entity_name


@pytest.mark.parametrize(
    "name",
    [
        "0.85",
        "0.95",
        "95%",
        "12",
        "1,000",
        "AUG89.LB",
        "feb92.lb",
        "0CT89.MP",
        "x",
        " ",
        "-",
    ],
)
def test_drops_junk(name):
    assert is_low_value_entity_name(name) is True


@pytest.mark.parametrize(
    "name",
    [
        "RED",
        "AQM",
        "CoDel",
        "Cox",
        "B-ISDN",
        "VBR video traffic",
        "1/f noise",
        "27 consecutive hours",
        "Hurst parameter H",
        "self-similar traffic",
    ],
)
def test_keeps_real_entities(name):
    assert is_low_value_entity_name(name) is False
