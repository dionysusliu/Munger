"""Single source of truth for the entity ontology used in all LLM prompts.

Every prompt that mentions entity types assembles its vocabulary from this
module. Never write a type list inline in a service.
"""

from __future__ import annotations

ENTITY_TYPES: dict[str, dict[str, str]] = {
    "person": {
        "definition": "A real, named individual (author, researcher, historical figure).",
        "example": "Charlie Munger",
        "counter_example": "'the author', 'a node operator' (unnamed roles are not entities)",
    },
    "organization": {
        "definition": "A named company, institution, or project.",
        "example": "BitTorrent",
        "counter_example": "'the committee' (unnamed body)",
    },
    "work": {
        "definition": "A named book, paper, article, or other published work.",
        "example": "Poor Charlie's Almanack",
        "counter_example": "'this paper', 'the cited study' (document-local references)",
    },
    "concept": {
        "definition": "A named domain concept that could carry its own encyclopedia page.",
        "example": "Consistent Hashing",
        "counter_example": "'Theorem 2', 'the second approach' (document-local labels)",
    },
    "mental_model": {
        "definition": "A cross-domain thinking tool or principle for reasoning about many situations.",
        "example": "Network Effects",
        "counter_example": "a domain-specific algorithm (that is a concept or mechanism)",
    },
    "mechanism": {
        "definition": "A named process or system with a causal chain, including incentive structures.",
        "example": "Proof of Stake",
        "counter_example": "vague processes like 'the workflow'",
    },
    "event": {
        "definition": "A named historical event.",
        "example": "Mt. Gox Collapse",
        "counter_example": "'the experiment in Section 3' (document-local)",
    },
}

ENTITY_TYPE_NAMES: tuple[str, ...] = tuple(ENTITY_TYPES)

TYPE_PRIORITY = (
    "If an entity fits multiple types, prefer: mental_model over mechanism over concept."
)

NAMING_RULES = """Entity naming rules:
1. SELF-EXPLANATORY NAME: the name must be recognizable outside this document.
2. NEVER extract document-local labels. Forbidden: 'Theorem N', 'Figure N', 'Table N', \
'Section N', 'Equation N', 'Chapter N', 'Lemma N', 'Appendix N', 'the author', \
'this paper', 'this book', 'the study'. If a theorem or figure describes a salient \
concept, extract the CONCEPT under its own descriptive name instead.
3. CANONICAL FORM: official full name, singular, no leading article. \
Prefer the full name over an acronym (use 'Content Identifier', not 'CID').
4. SALIENCE: extract only entities that could carry their own encyclopedia page."""


def ontology_block() -> str:
    """Render the closed type vocabulary with definitions and examples for prompts."""
    lines = ["Allowed entity types (closed vocabulary, use EXACTLY one of these):"]
    for name, info in ENTITY_TYPES.items():
        lines.append(
            f"- {name}: {info['definition']} Example: {info['example']}. "
            f"NOT: {info['counter_example']}."
        )
    lines.append("")
    lines.append(TYPE_PRIORITY)
    return "\n".join(lines)


# Exact mapping of the retired legacy vocabulary (used by migration 015 and
# runtime normalization). The five legacy names that survive unchanged in the
# 7-type vocab (person, organization, concept, mechanism, event) need no entry.
LEGACY_TYPE_MAPPING: dict[str, str] = {
    "book": "work",
    "paper": "work",
    "model": "mental_model",
    "principle": "mental_model",
    "incentive_structure": "mechanism",
    "field": "concept",
}

# Tolerant mapping for free-form LLM type labels (lower-cased, spaces -> underscores).
ALIAS_TYPE_MAPPING: dict[str, str] = {
    "people": "person",
    "individual": "person",
    "author": "person",
    "company": "organization",
    "institution": "organization",
    "article": "work",
    "publication": "work",
    "idea": "concept",
    "notion": "concept",
    "discipline": "concept",
    "domain": "concept",
    "framework": "mental_model",
    "law": "mental_model",
    "rule": "mental_model",
    "process": "mechanism",
    "system": "mechanism",
    "incentive": "mechanism",
    "incentives": "mechanism",
}
