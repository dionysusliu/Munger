"""Remap legacy 11-type entity vocabulary to the 7-type ontology (prompt overhaul phase 1).

Applies to both entities.entity_type and wiki_pages.page_type (wiki pages store
the entity type as their page_type). Downgrade is best-effort: merged types
cannot be split back precisely (work -> book, mental_model -> model; the
incentive_structure->mechanism and field->concept merges are not reversible).

Revision ID: 015_ontology_seven_types
Revises: 014_community_search_vector
Create Date: 2026-06-11
"""

from alembic import op

revision = "015_ontology_seven_types"
down_revision = "014_community_search_vector"
branch_labels = None
depends_on = None

UPGRADE_MAPPING = {
    "book": "work",
    "paper": "work",
    "model": "mental_model",
    "principle": "mental_model",
    "incentive_structure": "mechanism",
    "field": "concept",
}

DOWNGRADE_MAPPING = {
    "work": "book",
    "mental_model": "model",
}


def _apply(mapping: dict[str, str]) -> None:
    for old, new in mapping.items():
        op.execute(f"UPDATE entities SET entity_type = '{new}' WHERE entity_type = '{old}'")
        op.execute(f"UPDATE wiki_pages SET page_type = '{new}' WHERE page_type = '{old}'")


def upgrade() -> None:
    _apply(UPGRADE_MAPPING)


def downgrade() -> None:
    _apply(DOWNGRADE_MAPPING)
