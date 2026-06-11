"""_normalize_entity_type must map every raw label into the 7-type ontology."""

import pytest

pytestmark = pytest.mark.no_db

from app.prompts import ENTITY_TYPE_NAMES, LEGACY_TYPE_MAPPING
from app.services.entity_service import EntityService


@pytest.fixture()
def service():
    return EntityService(llm_service=None)


class TestNormalizeEntityType:
    def test_canonical_names_pass_through(self, service):
        for name in ENTITY_TYPE_NAMES:
            assert service._normalize_entity_type(name) == name

    def test_legacy_vocabulary_is_remapped(self, service):
        for old, new in LEGACY_TYPE_MAPPING.items():
            assert service._normalize_entity_type(old) == new

    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            # casing + space normalization (canonical path after " "->"_")
            ("Person", "person"),
            ("mental model", "mental_model"),
            ("Mental Model", "mental_model"),
            # legacy vocabulary, hardcoded as independent evidence
            ("book", "work"),
            ("paper", "work"),
            ("model", "mental_model"),
            ("principle", "mental_model"),
            ("incentive_structure", "mechanism"),
            ("field", "concept"),
            # alias layer — all 18 entries pinned to exact targets
            ("people", "person"),
            ("individual", "person"),
            ("author", "person"),
            ("company", "organization"),
            ("institution", "organization"),
            ("article", "work"),
            ("publication", "work"),
            ("idea", "concept"),
            ("notion", "concept"),
            ("discipline", "concept"),
            ("domain", "concept"),
            ("framework", "mental_model"),
            ("law", "mental_model"),
            ("rule", "mental_model"),
            ("process", "mechanism"),
            ("system", "mechanism"),
            ("incentive", "mechanism"),
            ("incentives", "mechanism"),
        ],
    )
    def test_aliases_and_casing(self, service, raw, expected):
        assert service._normalize_entity_type(raw) == expected

    def test_unknown_label_falls_back_to_concept(self, service):
        assert service._normalize_entity_type("gibberish_label") == "concept"

    def test_never_returns_a_type_outside_the_vocabulary(self, service):
        for raw in ("book", "PAPER", "model", "law", "system", "weird", "Field"):
            assert service._normalize_entity_type(raw) in ENTITY_TYPE_NAMES
