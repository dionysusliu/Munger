"""Unit tests for the centralized prompt module (app/prompts/)."""

import pytest

from app.prompts.ontology import (
    ALIAS_TYPE_MAPPING,
    ENTITY_TYPE_NAMES,
    ENTITY_TYPES,
    LEGACY_TYPE_MAPPING,
    NAMING_RULES,
    ontology_block,
)
from app.prompts.extraction import (
    EXTRACT_SYSTEM,
    GLEAN_SYSTEM,
    GLEAN_YES_NO_SYSTEM,
)
from app.prompts.wiki import (
    SUGGEST_LINKS_SYSTEM,
    WIKI_TYPE_PROMPTS,
    build_wiki_system,
)

pytestmark = pytest.mark.no_db


class TestOntologyVocabulary:
    def test_exactly_seven_types(self):
        assert set(ENTITY_TYPE_NAMES) == {
            "person",
            "organization",
            "work",
            "concept",
            "mental_model",
            "mechanism",
            "event",
        }

    def test_every_type_has_definition_and_examples(self):
        for name, info in ENTITY_TYPES.items():
            assert info["definition"], name
            assert info["example"], name
            assert info["counter_example"], name

    def test_legacy_mapping_covers_all_retired_types(self):
        assert set(LEGACY_TYPE_MAPPING) == {
            "book",
            "paper",
            "model",
            "principle",
            "incentive_structure",
            "field",
        }
        assert set(LEGACY_TYPE_MAPPING.values()) <= set(ENTITY_TYPE_NAMES)

    def test_alias_mapping_targets_valid_types(self):
        assert set(ALIAS_TYPE_MAPPING.values()) <= set(ENTITY_TYPE_NAMES)

    def test_ontology_block_lists_every_type_and_no_ellipsis(self):
        block = ontology_block()
        for name in ENTITY_TYPE_NAMES:
            assert name in block
        assert "..." not in block
        assert "mental_model over mechanism" in block

    def test_naming_rules_ban_document_local_labels(self):
        for banned in ("Theorem N", "Figure N", "Table N", "Section N"):
            assert banned in NAMING_RULES


class TestExtractionPrompts:
    def test_extract_system_contains_full_vocabulary(self):
        for name in ENTITY_TYPE_NAMES:
            assert name in EXTRACT_SYSTEM

    def test_extract_system_keeps_json_contract(self):
        assert '"entities"' in EXTRACT_SYSTEM
        assert '"relationships"' in EXTRACT_SYSTEM
        assert "char_start" in EXTRACT_SYSTEM

    def test_extract_system_dropped_the_ellipsis_type_list(self):
        assert "person|concept|model|..." not in EXTRACT_SYSTEM

    def test_glean_prompts_carry_naming_rules(self):
        assert "Theorem N" in GLEAN_SYSTEM
        assert "Theorem N" in GLEAN_YES_NO_SYSTEM

    def test_glean_yes_no_still_demands_yes_or_no(self):
        assert "YES or NO" in GLEAN_YES_NO_SYSTEM

    def test_glean_system_contains_full_vocabulary(self):
        for name in ENTITY_TYPE_NAMES:
            assert name in GLEAN_SYSTEM

    def test_glean_system_keeps_json_contract(self):
        assert '"missed_entities"' in GLEAN_SYSTEM
        assert '"missed_relationships"' in GLEAN_SYSTEM
        assert '"reasoning"' in GLEAN_SYSTEM


class TestWikiPrompts:
    def test_every_entity_type_has_a_page_prompt(self):
        for name in ENTITY_TYPE_NAMES:
            assert name in WIKI_TYPE_PROMPTS, name
        assert "summary" in WIKI_TYPE_PROMPTS

    def test_build_wiki_system_includes_title_and_quality_rules(self):
        system = build_wiki_system("Consistent Hashing", "concept")
        assert "Consistent Hashing" in system
        assert "[[" in system  # wikilink syntax taught
        assert "$" in system  # formula preservation rule present
        assert "Do not invent" in system  # grounding rule present

    def test_unknown_page_type_falls_back_gracefully(self):
        system = build_wiki_system("X", "no_such_type")
        assert "wiki page" in system
        assert "[[" in system  # rule blocks still injected
        assert "Do not invent" in system

    def test_suggest_links_keeps_json_contract(self):
        assert "to_page_id" in SUGGEST_LINKS_SYSTEM
        assert "link_type" in SUGGEST_LINKS_SYSTEM
        assert '"context"' in SUGGEST_LINKS_SYSTEM


class TestPackageExports:
    def test_all_prompts_importable_from_package_root(self):
        from app.prompts import (  # noqa: F401
            ALIAS_TYPE_MAPPING,
            ENTITY_TYPE_NAMES,
            ENTITY_TYPES,
            EXTRACT_SYSTEM,
            FORMULA_RULES,
            GLEAN_SYSTEM,
            GLEAN_YES_NO_SYSTEM,
            GROUNDING_RULES,
            LEGACY_TYPE_MAPPING,
            NAMING_RULES,
            PROF_MERGE_SYSTEM,
            SAME_ENTITY_SYSTEM,
            SUGGEST_LINKS_SYSTEM,
            TYPE_PRIORITY,
            WIKILINK_RULES,
            WIKI_TYPE_PROMPTS,
            build_wiki_system,
            ontology_block,
        )

    def test_prof_merge_keeps_math_notation(self):
        from app.prompts import PROF_MERGE_SYSTEM

        assert "$" in PROF_MERGE_SYSTEM

    def test_same_entity_keeps_json_contract(self):
        from app.prompts import SAME_ENTITY_SYSTEM

        assert '"same"' in SAME_ENTITY_SYSTEM
