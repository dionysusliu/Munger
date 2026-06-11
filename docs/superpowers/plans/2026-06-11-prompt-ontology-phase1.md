# Prompt Overhaul Phase 1 — Ontology Rebuild + Formula Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Centralize all LLM prompt text into a single `app/prompts/` module with a 7-type entity ontology (killing "Theorem 2"-style entities), and clean parser output so formulas render as KaTeX math instead of dead image refs.

**Architecture:** New `munger/backend/app/prompts/` package is the single source of truth (`ontology.py` → vocabulary/rules; `extraction.py`/`wiki.py`/`resolution.py` assemble prompts from it). Services import constants and never define prompt text inline. A pure-regex `text_normalizer.py` runs at the end of `StorageService.extract_text`, converting `![LaTeX](dead-path)` image refs to `$...$` math before anything downstream sees the text. One Alembic data migration remaps legacy entity/page types.

**Tech Stack:** Python 3.12 (FastAPI backend), pytest, Alembic/Postgres. Frontend needs **zero changes** — `WikiMarkdown.tsx` already wires `remark-math` + `rehype-katex` + KaTeX CSS; it just never receives `$...$` input today.

**Spec:** `docs/superpowers/specs/2026-06-11-prompt-ontology-design.md`

**Test command** (run from `munger/backend/`; ALWAYS use the 3.12 venv, never system python):

```bash
TEST_DATABASE_URL=postgresql+psycopg://munger_app:Munger.App.2026@localhost:5432/munger_test \
  /Users/chuang/Documents/dev/projects/Munger/munger/backend/.venv/bin/python -m pytest <PATH> -q -p no:cacheprovider
```

Referred to below as `PYTEST <PATH>`. The full-suite run additionally needs
`--ignore=tests/integration/test_provider_gate.py --ignore=tests/integration/test_frontend_smoke.py`.
Baseline before this plan: **178 passed**.

---

## Current state (what you are changing)

| Location | Today | After |
|---|---|---|
| `app/services/extraction_service.py:22-29` | Local `EXTRACT_SYSTEM` (type list literally ends `\|...`), `GLEAN_SYSTEM` | Imports from `app.prompts` |
| `app/services/map_chunk_service.py:34-46` | Duplicate `EXTRACT_SYSTEM`, `GLEAN_YES_NO_SYSTEM`, `GLEAN_CONTINUE_SYSTEM` | Imports from `app.prompts` |
| `app/services/llm_service.py:733-755` | `extract_entities` with inline 11-type vocab | 7-type vocab from ontology |
| `app/services/llm_service.py:803-836` | `generate_wiki_page` with 8 one-line `type_prompts` that miss `person`/`book`/`paper`/`organization` | `build_wiki_system()` covering all 7 types + summary, with wikilink/formula/grounding rules |
| `app/services/llm_service.py:838-871` | `suggest_links` inline prompt | Constant from `app.prompts` |
| `app/services/entity_service.py:310-344` | `_normalize_entity_type` with 11-type mapping | 7-type mapping from ontology |
| `app/services/resolution_service.py:23-26` | Local `PROF_MERGE_SYSTEM` | Import |
| `app/services/linking_service.py:241-258` | `_llm_same_entity` inline prompt | Import |
| `app/services/storage_service.py:176-201` | `extract_text` returns raw parser output | Output passes through `normalize_extracted_text` |
| DB | `entities.entity_type` / `wiki_pages.page_type` hold legacy values (`book`, `paper`, `model`, `principle`, `incentive_structure`, `field`) | Migration 015 remaps to 7-type vocab |

Both columns are plain `String(50)` (no Postgres enum), so the migration is pure `UPDATE`s.

---

### Task 1: Ontology single source of truth

**Files:**
- Create: `munger/backend/app/prompts/__init__.py` (empty for now; filled in Task 4)
- Create: `munger/backend/app/prompts/ontology.py`
- Test: `munger/backend/tests/unit/test_prompts.py`

- [ ] **Step 1: Write the failing test**

Create `munger/backend/tests/unit/test_prompts.py`:

```python
"""Unit tests for the centralized prompt module (app/prompts/)."""

from app.prompts.ontology import (
    ALIAS_TYPE_MAPPING,
    ENTITY_TYPE_NAMES,
    ENTITY_TYPES,
    LEGACY_TYPE_MAPPING,
    NAMING_RULES,
    ontology_block,
)


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

    def test_naming_rules_ban_document_local_labels(self):
        for banned in ("Theorem N", "Figure N", "Table N", "Section N"):
            assert banned in NAMING_RULES
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTEST tests/unit/test_prompts.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.prompts'`

- [ ] **Step 3: Write the implementation**

Create empty `munger/backend/app/prompts/__init__.py` and then `munger/backend/app/prompts/ontology.py`:

```python
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
    lines.append(TYPE_PRIORITY)
    return "\n".join(lines)


# Exact mapping of the retired legacy vocabulary (used by migration 015 and
# runtime normalization). The other five legacy names survive unchanged.
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTEST tests/unit/test_prompts.py`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add munger/backend/app/prompts/ munger/backend/tests/unit/test_prompts.py
git commit -m "feat(prompts): ontology module — 7-type vocabulary, naming rules, legacy mappings"
```

---

### Task 2: Extraction & glean prompts

**Files:**
- Create: `munger/backend/app/prompts/extraction.py`
- Test: `munger/backend/tests/unit/test_prompts.py` (extend)

- [ ] **Step 1: Write the failing test**

Append to `munger/backend/tests/unit/test_prompts.py`:

```python
from app.prompts.extraction import (
    EXTRACT_SYSTEM,
    GLEAN_SYSTEM,
    GLEAN_YES_NO_SYSTEM,
)


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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTEST tests/unit/test_prompts.py`
Expected: FAIL — `ImportError: cannot import name 'EXTRACT_SYSTEM' from 'app.prompts.extraction'` (module missing)

- [ ] **Step 3: Write the implementation**

Create `munger/backend/app/prompts/extraction.py`:

```python
"""Per-chunk extraction and glean prompts, assembled from the ontology."""

from __future__ import annotations

from app.prompts.ontology import NAMING_RULES, ontology_block

# JSON keys must stay aligned with app/schemas/extraction.py
# (ExtractionResult / GleanResult) — do not rename fields here.
EXTRACT_SYSTEM = f"""Extract entities and relationships from the chunk text.

{ontology_block()}

{NAMING_RULES}

Return ONLY JSON matching:
{{"entities":[{{"name":"Entity Name","type":"one allowed type","description":"brief description","char_start":0,"char_end":0}}],
 "relationships":[{{"source":"Entity A","target":"Entity B","type":"relates_to","description":"brief description"}}]}}
Use document-global char offsets when possible. Include all salient entities."""

GLEAN_YES_NO_SYSTEM = f"""Were important entities missed in the prior extraction for this chunk?
Only count entities that satisfy these rules:

{NAMING_RULES}

Answer with exactly YES or NO."""

GLEAN_SYSTEM = f"""Some entities may have been missed in the first pass.

{ontology_block()}

{NAMING_RULES}

Return ONLY JSON:
{{"missed_entities":[],"missed_relationships":[],"reasoning":"why these were missed"}}
Populate missed_entities / missed_relationships with the same object shapes as the
original extraction (name, type, description, char_start, char_end)."""
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTEST tests/unit/test_prompts.py`
Expected: 11 passed

- [ ] **Step 5: Commit**

```bash
git add munger/backend/app/prompts/extraction.py munger/backend/tests/unit/test_prompts.py
git commit -m "feat(prompts): extraction/glean prompts assembled from ontology"
```

---

### Task 3: Wiki generation prompts

**Files:**
- Create: `munger/backend/app/prompts/wiki.py`
- Test: `munger/backend/tests/unit/test_prompts.py` (extend)

- [ ] **Step 1: Write the failing test**

Append to `munger/backend/tests/unit/test_prompts.py`:

```python
from app.prompts.wiki import (
    SUGGEST_LINKS_SYSTEM,
    WIKI_TYPE_PROMPTS,
    build_wiki_system,
)


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

    def test_suggest_links_keeps_json_contract(self):
        assert "to_page_id" in SUGGEST_LINKS_SYSTEM
        assert "link_type" in SUGGEST_LINKS_SYSTEM
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTEST tests/unit/test_prompts.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.prompts.wiki'`

- [ ] **Step 3: Write the implementation**

Create `munger/backend/app/prompts/wiki.py`:

```python
"""Wiki page generation prompts: per-type templates plus shared quality rules."""

from __future__ import annotations

WIKILINK_RULES = """Wikilink rules:
- Use [[Page Name]] syntax for internal links to important concepts.
- A [[link]] target must be a canonical concept name that could carry its own page \
(e.g. [[Consistent Hashing]]), never a sentence fragment or generic phrase.
- Linking to pages that do not exist yet is allowed and encouraged for salient concepts."""

FORMULA_RULES = """Formula rules:
- Keep math exactly as written in the source, wrapped in $...$ (inline) or $$...$$ (block).
- Never convert math into images and never alter LaTeX commands."""

GROUNDING_RULES = """Grounding rules:
- Use ONLY the provided material. Do not invent facts, numbers, or citations.
- If the material is thin, write a short page. Never pad."""

WIKI_TYPE_PROMPTS: dict[str, str] = {
    "summary": (
        "Create a well-structured summary wiki page for a source document. "
        "Sections: Overview, Key Points, Notable Entities."
    ),
    "person": (
        "Create a person wiki page. "
        "Sections: Overview, Role and Significance, Key Ideas, Related Concepts."
    ),
    "organization": (
        "Create an organization wiki page. "
        "Sections: Overview, Mission and Activities, Significance, Related Concepts."
    ),
    "work": (
        "Create a wiki page about a published work. "
        "Sections: Overview, Core Arguments, Key Concepts, Influence."
    ),
    "concept": (
        "Create a concept wiki page. "
        "Sections: Definition, How It Works, Examples, Related Concepts."
    ),
    "mental_model": (
        "Create a mental model wiki page. "
        "Sections: Definition, When To Apply, Examples Across Domains, Related Mental Models."
    ),
    "mechanism": (
        "Create a mechanism wiki page. "
        "Sections: Overview, Causal Chain (step by step), Incentives at Play, Examples."
    ),
    "event": (
        "Create an event wiki page. "
        "Sections: Overview, Timeline, Causes, Consequences, Lessons."
    ),
}

_FALLBACK_PROMPT = "Create a well-structured wiki page in markdown format."


def build_wiki_system(title: str, page_type: str) -> str:
    """System prompt for generate_wiki_page; covers all 7 entity types + summary."""
    type_prompt = WIKI_TYPE_PROMPTS.get(page_type, _FALLBACK_PROMPT)
    return (
        f"You are a wiki editor. {type_prompt}\n"
        "Use markdown formatting with headers and lists.\n"
        f"{WIKILINK_RULES}\n\n{FORMULA_RULES}\n\n{GROUNDING_RULES}\n\n"
        f"Title: {title}"
    )


SUGGEST_LINKS_SYSTEM = (
    "Suggest relevant wiki links from the given page content to existing pages.\n"
    "Return ONLY a JSON array of objects:\n"
    '[{"to_page_id": 1, "link_type": "reference|contradicts|supports|relates", '
    '"context": "Why this link is relevant"}]\n'
    "Only suggest genuinely relevant connections. Return ONLY the JSON array."
)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTEST tests/unit/test_prompts.py`
Expected: 15 passed

- [ ] **Step 5: Commit**

```bash
git add munger/backend/app/prompts/wiki.py munger/backend/tests/unit/test_prompts.py
git commit -m "feat(prompts): wiki page prompts — full type coverage, wikilink/formula/grounding rules"
```

---

### Task 4: Resolution prompts + package exports

**Files:**
- Create: `munger/backend/app/prompts/resolution.py`
- Modify: `munger/backend/app/prompts/__init__.py`
- Test: `munger/backend/tests/unit/test_prompts.py` (extend)

- [ ] **Step 1: Write the failing test**

Append to `munger/backend/tests/unit/test_prompts.py`:

```python
class TestPackageExports:
    def test_all_prompts_importable_from_package_root(self):
        from app.prompts import (  # noqa: F401
            ALIAS_TYPE_MAPPING,
            ENTITY_TYPE_NAMES,
            ENTITY_TYPES,
            EXTRACT_SYSTEM,
            GLEAN_SYSTEM,
            GLEAN_YES_NO_SYSTEM,
            LEGACY_TYPE_MAPPING,
            NAMING_RULES,
            PROF_MERGE_SYSTEM,
            SAME_ENTITY_SYSTEM,
            SUGGEST_LINKS_SYSTEM,
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTEST tests/unit/test_prompts.py`
Expected: FAIL — `ImportError` (resolution module and re-exports missing)

- [ ] **Step 3: Write the implementation**

Create `munger/backend/app/prompts/resolution.py`:

```python
"""Entity resolution prompts: description merging and co-reference checks."""

PROF_MERGE_SYSTEM = (
    "Merge these entity descriptions into one concise summary (max 512 chars). "
    "Preserve key facts from all sources. Keep any $...$ math notation intact."
)

SAME_ENTITY_SYSTEM = (
    "Do A and B refer to the same real-world entity? "
    "Consider name variants, acronyms, and translations. "
    'JSON only: {"same": true|false}'
)
```

Replace `munger/backend/app/prompts/__init__.py` with:

```python
"""Centralized prompt module — single source of truth for all LLM prompt text."""

from app.prompts.extraction import (
    EXTRACT_SYSTEM,
    GLEAN_SYSTEM,
    GLEAN_YES_NO_SYSTEM,
)
from app.prompts.ontology import (
    ALIAS_TYPE_MAPPING,
    ENTITY_TYPE_NAMES,
    ENTITY_TYPES,
    LEGACY_TYPE_MAPPING,
    NAMING_RULES,
    TYPE_PRIORITY,
    ontology_block,
)
from app.prompts.resolution import PROF_MERGE_SYSTEM, SAME_ENTITY_SYSTEM
from app.prompts.wiki import (
    FORMULA_RULES,
    GROUNDING_RULES,
    SUGGEST_LINKS_SYSTEM,
    WIKI_TYPE_PROMPTS,
    WIKILINK_RULES,
    build_wiki_system,
)

__all__ = [
    "ALIAS_TYPE_MAPPING",
    "ENTITY_TYPE_NAMES",
    "ENTITY_TYPES",
    "EXTRACT_SYSTEM",
    "FORMULA_RULES",
    "GLEAN_SYSTEM",
    "GLEAN_YES_NO_SYSTEM",
    "GROUNDING_RULES",
    "LEGACY_TYPE_MAPPING",
    "NAMING_RULES",
    "PROF_MERGE_SYSTEM",
    "SAME_ENTITY_SYSTEM",
    "SUGGEST_LINKS_SYSTEM",
    "TYPE_PRIORITY",
    "WIKILINK_RULES",
    "WIKI_TYPE_PROMPTS",
    "build_wiki_system",
    "ontology_block",
]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTEST tests/unit/test_prompts.py`
Expected: 18 passed

- [ ] **Step 5: Commit**

```bash
git add munger/backend/app/prompts/
git add munger/backend/tests/unit/test_prompts.py
git commit -m "feat(prompts): resolution prompts + package-root exports"
```

---

### Task 5: Switch extraction services to the prompt module

**Files:**
- Modify: `munger/backend/app/services/extraction_service.py:22-29`
- Modify: `munger/backend/app/services/map_chunk_service.py:34-46,161`

- [ ] **Step 1: Replace local constants in extraction_service.py**

Delete lines 22–29 (both constants):

```python
EXTRACT_SYSTEM = """Extract entities and relationships from the chunk text.
Return ONLY JSON matching:
{"entities":[{"name":"...","type":"person|concept|model|...","description":"...","char_start":0,"char_end":0}],
 "relationships":[{"source":"...","target":"...","type":"relates_to","description":"..."}]}
Use document-global char offsets when possible. Include all salient entities."""

GLEAN_SYSTEM = """Many entities were missed in the first pass. Return ONLY JSON:
{"missed_entities":[...],"missed_relationships":[...],"reasoning":"..."}"""
```

and add to the imports block (after `from app.models.source import Source`):

```python
from app.prompts import EXTRACT_SYSTEM, GLEAN_SYSTEM
```

- [ ] **Step 2: Replace local constants in map_chunk_service.py**

Delete lines 34–46 (all three constants):

```python
EXTRACT_SYSTEM = """Extract entities and relationships from the chunk text.
Return ONLY JSON matching:
{"entities":[{"name":"...","type":"person|concept|model|...","description":"...","char_start":0,"char_end":0}],
 "relationships":[{"source":"...","target":"...","type":"relates_to","description":"..."}]}
Use document-global char offsets when possible. Include all salient entities."""

GLEAN_YES_NO_SYSTEM = (
    "Were important entities missed in the prior extraction for this chunk? "
    "Answer with exactly YES or NO."
)

GLEAN_CONTINUE_SYSTEM = """Many entities were missed in the first pass. Return ONLY JSON:
{"missed_entities":[...],"missed_relationships":[...],"reasoning":"..."}"""
```

add to the imports block (after `from app.models.source import Source`):

```python
from app.prompts import EXTRACT_SYSTEM, GLEAN_SYSTEM, GLEAN_YES_NO_SYSTEM
```

and at line 161 (the only `GLEAN_CONTINUE_SYSTEM` usage) change:

```python
            {"role": "system", "content": GLEAN_CONTINUE_SYSTEM},
```

to:

```python
            {"role": "system", "content": GLEAN_SYSTEM},
```

- [ ] **Step 3: Run the affected unit tests**

Run: `PYTEST tests/unit/test_map_chunk_service.py tests/unit/test_chunk_service.py tests/unit/test_cross_chunk_golden.py tests/unit/test_reduce_prof_merge.py`
Expected: all pass (these tests mock the LLM; no test asserts prompt text — verified by grep)

- [ ] **Step 4: Commit**

```bash
git add munger/backend/app/services/extraction_service.py munger/backend/app/services/map_chunk_service.py
git commit -m "refactor(extraction): use centralized prompts, kill duplicated ellipsis vocab"
```

---

### Task 6: Switch llm_service to the prompt module

**Files:**
- Modify: `munger/backend/app/services/llm_service.py:733-755` (`extract_entities`), `:803-836` (`generate_wiki_page`), `:838-871` (`suggest_links`)

- [ ] **Step 1: Add imports**

In the import block at the top of `llm_service.py`, add:

```python
from app.prompts import (
    ENTITY_TYPE_NAMES,
    NAMING_RULES,
    SUGGEST_LINKS_SYSTEM,
    build_wiki_system,
    ontology_block,
)
```

(`app.prompts` imports nothing from `app.services`, so there is no circular-import risk.)

- [ ] **Step 2: Rewrite `extract_entities` system message**

Replace the `messages` construction in `extract_entities` (lines 736–750):

```python
        messages = [
            {
                "role": "system",
                "content": (
                    "Extract named entities from the following text. "
                    "Return ONLY a JSON array of objects with this exact format:\n"
                    '[{"name": "Entity Name", "type": "person|concept|model|'
                    'mechanism|incentive_structure|book|paper|organization|'
                    'field|event|principle", "description": "Brief description"}]\n'
                    "Include only the most important and frequently mentioned entities. "
                    "Return ONLY the JSON array, no other text."
                ),
            },
            {"role": "user", "content": truncated},
        ]
```

with:

```python
        type_choices = "|".join(ENTITY_TYPE_NAMES)
        messages = [
            {
                "role": "system",
                "content": (
                    "Extract named entities from the following text.\n"
                    f"{ontology_block()}\n\n"
                    f"{NAMING_RULES}\n\n"
                    "Return ONLY a JSON array of objects with this exact format:\n"
                    f'[{{"name": "Entity Name", "type": "{type_choices}", '
                    '"description": "Brief description"}]\n'
                    "Include only the most important and frequently mentioned entities. "
                    "Return ONLY the JSON array, no other text."
                ),
            },
            {"role": "user", "content": truncated},
        ]
```

- [ ] **Step 3: Rewrite `generate_wiki_page`**

Replace the body between `truncated = ...` and the `try:` (lines 808–832 — the whole `type_prompts` dict, `prompt = ...`, and `messages = ...`):

```python
        type_prompts = {
            "summary": "Create a well-structured summary wiki page.",
            "entity": "Create a detailed entity wiki page with background, significance, and related concepts.",
            "concept": "Create a concept wiki page with definition, examples, and related mental models.",
            "model": "Create a mental model wiki page with explanation, examples, and applications.",
            "mechanism": "Create a mechanism wiki page explaining how it works with causal chains.",
            "incentive": "Create an incentive structure wiki page with stakeholder analysis.",
            "psychology": "Create a psychology wiki page about cognitive biases and mental patterns.",
            "analysis": "Create an analysis wiki page with structured reasoning.",
        }
        prompt = type_prompts.get(
            page_type, "Create a well-structured wiki page in markdown format."
        )
        messages = [
            {
                "role": "system",
                "content": (
                    f"You are a wiki editor. {prompt}\n"
                    "Use markdown formatting with headers, lists, and links.\n"
                    "Use [[Page Name]] syntax for internal wiki links where relevant.\n"
                    f"Title: {title}"
                ),
            },
            {"role": "user", "content": truncated},
        ]
```

with:

```python
        messages = [
            {"role": "system", "content": build_wiki_system(title, page_type)},
            {"role": "user", "content": truncated},
        ]
```

- [ ] **Step 4: Rewrite `suggest_links` system message**

Replace the system dict content in `suggest_links` (lines 852–861):

```python
            {
                "role": "system",
                "content": (
                    "Suggest relevant wiki links from the given page content to existing pages.\n"
                    "Return ONLY a JSON array of objects:\n"
                    '[{"to_page_id": 1, "link_type": "reference|contradicts|supports|relates", '
                    '"context": "Why this link is relevant"}]\n'
                    "Only suggest genuinely relevant connections. Return ONLY the JSON array."
                ),
            },
```

with:

```python
            {"role": "system", "content": SUGGEST_LINKS_SYSTEM},
```

- [ ] **Step 5: Run the affected unit tests**

Run: `PYTEST tests/unit/test_llm_service_openrouter.py tests/unit/test_llm_adapter.py tests/unit/test_prompts.py`
Expected: all pass

- [ ] **Step 6: Commit**

```bash
git add munger/backend/app/services/llm_service.py
git commit -m "refactor(llm): wiki/extract/suggest prompts from centralized module — full page_type coverage"
```

---

### Task 7: Normalize entity types against the new vocabulary

**Files:**
- Modify: `munger/backend/app/services/entity_service.py:310-344`
- Test: `munger/backend/tests/unit/test_entity_type_normalization.py` (new)

- [ ] **Step 1: Write the failing test**

Create `munger/backend/tests/unit/test_entity_type_normalization.py`:

```python
"""_normalize_entity_type must map every raw label into the 7-type ontology."""

import pytest

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
            ("Person", "person"),
            ("mental model", "mental_model"),
            ("Mental Model", "mental_model"),
            ("framework", "mental_model"),
            ("company", "organization"),
            ("article", "work"),
            ("incentive", "mechanism"),
            ("idea", "concept"),
        ],
    )
    def test_aliases_and_casing(self, service, raw, expected):
        assert service._normalize_entity_type(raw) == expected

    def test_unknown_label_falls_back_to_concept(self, service):
        assert service._normalize_entity_type("gibberish_label") == "concept"

    def test_never_returns_a_type_outside_the_vocabulary(self, service):
        for raw in ("book", "PAPER", "model", "law", "system", "weird", "Field"):
            assert service._normalize_entity_type(raw) in ENTITY_TYPE_NAMES
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTEST tests/unit/test_entity_type_normalization.py`
Expected: FAIL — legacy labels like `"book"` currently return `"book"`, not `"work"`

- [ ] **Step 3: Rewrite `_normalize_entity_type`**

In `entity_service.py`, add to the imports:

```python
from app.prompts import ALIAS_TYPE_MAPPING, ENTITY_TYPES, LEGACY_TYPE_MAPPING
```

Replace the whole method (lines 310–344, the 33-line `type_mapping` dict version) with:

```python
    def _normalize_entity_type(self, entity_type: str) -> str:
        """Normalize a raw LLM type label to the 7-type ontology vocabulary."""
        key = entity_type.lower().strip().replace(" ", "_")
        if key in ENTITY_TYPES:
            return key
        if key in LEGACY_TYPE_MAPPING:
            return LEGACY_TYPE_MAPPING[key]
        return ALIAS_TYPE_MAPPING.get(key, "concept")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTEST tests/unit/test_entity_type_normalization.py`
Expected: all pass

- [ ] **Step 5: Commit**

```bash
git add munger/backend/app/services/entity_service.py munger/backend/tests/unit/test_entity_type_normalization.py
git commit -m "refactor(entity): normalize types against 7-type ontology"
```

---

### Task 8: Switch resolution & linking services

**Files:**
- Modify: `munger/backend/app/services/resolution_service.py:23-26`
- Modify: `munger/backend/app/services/linking_service.py:241-258`

- [ ] **Step 1: resolution_service.py**

Delete the local constant (lines 23–26):

```python
PROF_MERGE_SYSTEM = (
    "Merge these entity descriptions into one concise summary (max 512 chars). "
    "Preserve key facts from all sources."
)
```

Add to imports:

```python
from app.prompts import PROF_MERGE_SYSTEM
```

- [ ] **Step 2: linking_service.py**

Add to imports:

```python
from app.prompts import SAME_ENTITY_SYSTEM
```

In `_llm_same_entity` (line 244–248) replace:

```python
            {
                "role": "system",
                "content": 'Same real-world entity? JSON only: {"same": true|false}',
            },
```

with:

```python
            {"role": "system", "content": SAME_ENTITY_SYSTEM},
```

- [ ] **Step 3: Run the affected unit tests**

Run: `PYTEST tests/unit/test_reduce_prof_merge.py tests/unit/test_linking_service.py`
Expected: all pass

- [ ] **Step 4: Commit**

```bash
git add munger/backend/app/services/resolution_service.py munger/backend/app/services/linking_service.py
git commit -m "refactor(resolution): prof-merge + same-entity prompts from centralized module"
```

---

### Task 9: Text normalizer — formulas to `$...$`, dead figures to placeholders

**Files:**
- Create: `munger/backend/app/services/text_normalizer.py`
- Modify: `munger/backend/app/services/storage_service.py:176-201` (`extract_text`)
- Test: `munger/backend/tests/unit/test_text_normalizer.py` (new)

Frontend note: **no frontend work** — `app/src/components/wiki/WikiMarkdown.tsx` already loads `remark-math`, `rehype-katex`, and `katex/dist/katex.min.css`; once `$...$` reaches page content it renders. KaTeX error tolerance is also covered: rehype-katex's default behavior on a malformed formula is to render the raw source in an error color without crashing the page, which satisfies the spec's `throwOnError: false` intent with zero config.

- [ ] **Step 1: Write the failing test**

Create `munger/backend/tests/unit/test_text_normalizer.py`:

```python
"""Parser-output normalization: formula image refs -> $...$, dead figures -> placeholders."""

import app.services.text_normalizer as tn
from app.services.text_normalizer import normalize_extracted_text


class TestFormulaImages:
    def test_latex_alt_becomes_inline_math(self):
        text = r"resolved with ![O(\log N)](page3_img1.png) messages"
        assert normalize_extracted_text(text) == r"resolved with $O(\log N)$ messages"

    def test_subscript_braces_count_as_latex(self):
        text = "value ![x_{i}](img.png) here"
        assert normalize_extracted_text(text) == "value $x_{i}$ here"

    def test_long_latex_becomes_block_math(self):
        formula = r"\sum_{i=1}^{N} \frac{\log N}{2} + \mathbb{E}[X_i] - \epsilon_{threshold}"
        assert len(formula) > 60
        text = f"![{formula}](img.png)"
        assert normalize_extracted_text(text) == f"\n$$\n{formula}\n$$\n"


class TestPlainImages:
    def test_plain_alt_becomes_figure_placeholder(self):
        text = "see ![Chord ring topology](fig2.png) for details"
        assert (
            normalize_extracted_text(text)
            == "see *[Figure: Chord ring topology]* for details"
        )

    def test_empty_alt_image_is_removed(self):
        assert normalize_extracted_text("before ![](img.png) after") == "before  after"


class TestPassThrough:
    def test_text_without_images_is_unchanged(self):
        text = "Plain paragraph with $existing$ math and [a link](http://x)."
        assert normalize_extracted_text(text) == text

    def test_error_falls_back_to_raw_text(self, monkeypatch):
        def boom(*args, **kwargs):
            raise RuntimeError("replacement exploded")

        # _IMAGE_RE.sub resolves _replace_image from module globals at call
        # time, so patching the function makes the sub() call raise.
        monkeypatch.setattr(tn, "_replace_image", boom)
        assert normalize_extracted_text("has ![x](y.png) image") == "has ![x](y.png) image"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTEST tests/unit/test_text_normalizer.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.text_normalizer'`

- [ ] **Step 3: Write the implementation**

Create `munger/backend/app/services/text_normalizer.py`:

```python
"""Normalize parser output before chunking.

PDF parsing (LiteParse OCR) emits formulas as markdown image refs whose alt
text is the LaTeX source and whose path is dead — e.g. ``![O(\\log N)](p3.png)``.
Downstream (chunks, embeddings, wiki prompts) should see ``$O(\\log N)$`` instead.
Plain figures get a text placeholder since their paths are unreachable anyway.
"""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

_IMAGE_RE = re.compile(r"!\[(?P<alt>[^\]]*)\]\((?P<path>[^)]*)\)")
# LaTeX fingerprints: a backslash command, or sub/superscript braces.
_LATEX_HINT_RE = re.compile(r"\\[a-zA-Z]+|[_^]\{")
_BLOCK_MATH_THRESHOLD = 60


def _replace_image(match: re.Match[str]) -> str:
    alt = match.group("alt").strip()
    if not alt:
        return ""
    if _LATEX_HINT_RE.search(alt):
        if len(alt) > _BLOCK_MATH_THRESHOLD:
            return f"\n$$\n{alt}\n$$\n"
        return f"${alt}$"
    return f"*[Figure: {alt}]*"


def normalize_extracted_text(text: str) -> str:
    """Clean parser artifacts; on any internal error return the input unchanged."""
    try:
        return _IMAGE_RE.sub(_replace_image, text)
    except Exception as exc:
        logger.warning("Text normalization failed, keeping raw text: %s", exc)
        return text
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTEST tests/unit/test_text_normalizer.py`
Expected: 7 passed

- [ ] **Step 5: Wire into `StorageService.extract_text`**

In `storage_service.py`, add to imports:

```python
from app.services.text_normalizer import normalize_extracted_text
```

Replace the dispatch body of `extract_text` (lines 184–201):

```python
        try:
            if file_type == "pdf":
                return await self._extract_pdf(full_path)
            elif file_type in ("html", "htm", "url"):
                return await self._extract_html(full_path)
            elif file_type in ("md", "markdown"):
                return await self._extract_markdown(full_path)
            elif file_type in ("txt", "text"):
                return await self._extract_text_file(full_path)
            elif file_type in ("docx", "doc"):
                return await self._extract_docx(full_path)
            else:
                # Fallback: try to read as text
                logger.warning(f"Unknown file type '{file_type}', attempting text extraction")
                return await self._extract_text_file(full_path)
        except Exception as e:
            logger.error(f"Text extraction failed for {full_path}: {e}")
            raise TextExtractionError(f"Failed to extract text from {file_type}: {e}") from e
```

with:

```python
        try:
            if file_type == "pdf":
                text = await self._extract_pdf(full_path)
            elif file_type in ("html", "htm", "url"):
                text = await self._extract_html(full_path)
            elif file_type in ("md", "markdown"):
                text = await self._extract_markdown(full_path)
            elif file_type in ("txt", "text"):
                text = await self._extract_text_file(full_path)
            elif file_type in ("docx", "doc"):
                text = await self._extract_docx(full_path)
            else:
                # Fallback: try to read as text
                logger.warning(f"Unknown file type '{file_type}', attempting text extraction")
                text = await self._extract_text_file(full_path)
            return normalize_extracted_text(text)
        except Exception as e:
            logger.error(f"Text extraction failed for {full_path}: {e}")
            raise TextExtractionError(f"Failed to extract text from {file_type}: {e}") from e
```

- [ ] **Step 6: Run storage-related tests**

Run: `PYTEST tests/unit/test_text_normalizer.py tests/unit/test_backfill_source.py`
Expected: all pass

- [ ] **Step 7: Commit**

```bash
git add munger/backend/app/services/text_normalizer.py munger/backend/app/services/storage_service.py munger/backend/tests/unit/test_text_normalizer.py
git commit -m "feat(parse): normalize parser output — formula image refs to \$...\$, dead figures to placeholders"
```

---

### Task 10: Data migration — legacy types to the 7-type vocabulary

**Files:**
- Create: `munger/backend/alembic/versions/015_ontology_seven_types.py`

Both `entities.entity_type` and `wiki_pages.page_type` are `String(50)` — plain `UPDATE`s, no enum surgery. `wiki_pages.page_type` holds entity types because `nodes_cognify.py` passes `entity.entity_type` as `page_type`.

- [ ] **Step 1: Write the migration**

Create `munger/backend/alembic/versions/015_ontology_seven_types.py`:

```python
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
```

- [ ] **Step 2: Verify the migration applies**

The test conftest runs `alembic upgrade head` against `munger_test` once per session (`_run_migrations_once`), so running any test exercises the migration:

Run: `PYTEST tests/unit/test_prompts.py`
Expected: passes, and the output contains no Alembic errors. If you need to inspect manually:

```bash
cd munger/backend && DATABASE_URL=postgresql+psycopg://munger_app:Munger.App.2026@localhost:5432/munger_test \
  /Users/chuang/Documents/dev/projects/Munger/munger/backend/.venv/bin/python -m alembic current
```

Expected: `015_ontology_seven_types (head)`

- [ ] **Step 3: Commit**

```bash
git add munger/backend/alembic/versions/015_ontology_seven_types.py
git commit -m "feat(db): migration 015 — remap legacy entity/page types to 7-type ontology"
```

---

### Task 11: Full suite, docs sync, finish

**Files:**
- Modify: `ARCHITECTURE.md` (add subsection under `## Backend architecture`)
- Modify: `docs/superpowers/STATUS.md` (plans table + test count + date)

- [ ] **Step 1: Run the full backend suite**

```bash
cd munger/backend && TEST_DATABASE_URL=postgresql+psycopg://munger_app:Munger.App.2026@localhost:5432/munger_test \
  /Users/chuang/Documents/dev/projects/Munger/munger/backend/.venv/bin/python -m pytest tests/ -q -p no:cacheprovider \
  --ignore=tests/integration/test_provider_gate.py --ignore=tests/integration/test_frontend_smoke.py
```

Expected: **≥ 178 passed** (baseline 178 + ~20 new prompt/normalizer/normalization tests), 0 failed. Record the exact count for STATUS.md.

- [ ] **Step 2: Frontend sanity (no code changes expected)**

```bash
cd app && npm run lint && npm run build
```

Expected: both succeed without touching frontend code.

- [ ] **Step 3: Update ARCHITECTURE.md**

Insert at the end of the `## Backend architecture` section (immediately before the `## Ingest pipeline (LangGraph subgraphs)` heading at line 136):

```markdown
### Entity ontology & prompt module

All LLM prompt text lives in `munger/backend/app/prompts/` — `ontology.py` is the
single source of truth for the 7-type entity vocabulary (`person`, `organization`,
`work`, `concept`, `mental_model`, `mechanism`, `event`), the naming rules
(document-local labels like "Theorem 2" are never extracted), and the legacy-type
mappings applied by migration 015. `extraction.py` / `wiki.py` / `resolution.py`
assemble the extraction, wiki-generation, and resolution prompts from it; services
import these constants and never define prompt text inline.

Parser output is cleaned by `app/services/text_normalizer.py` before chunking:
formula image refs (`![O(\log N)](dead.png)`) become `$...$` inline math and dead
figure refs become `*[Figure: alt]*` placeholders, so math renders through the
frontend's existing remark-math + KaTeX chain. Generated `[[wikilinks]]` may point
to pages that don't exist yet (red links) — they render as `?unresolved` and are
the feedstock for the phase-2 enrichment pipeline.
```

- [ ] **Step 4: Update STATUS.md**

In `docs/superpowers/STATUS.md`:

1. Update the `Last updated` date on line 3 to the current date.
2. Update the test count line (`Current: **178 passed**`) with the count from Step 1.
3. Append this row to the execution plans table:

```markdown
| `2026-06-11-prompt-ontology-phase1.md` | ✅ DONE — 7-type ontology + `app/prompts/` module + `text_normalizer` ($...$ math) + mig 015; phase 2 (enrichment) not started |
```

- [ ] **Step 5: Commit**

```bash
git add ARCHITECTURE.md docs/superpowers/STATUS.md
git commit -m "docs: ontology + prompt module + text normalizer in ARCHITECTURE/STATUS"
```

- [ ] **Step 6: Manual acceptance checklist (needs a running stack + one PDF re-ingest)**

Re-ingest a math-heavy PDF (`docker compose up -d` in `munger/`, upload via the UI or `POST /api/sources/{id}/ingest`) and verify:

1. No `Theorem N` / `Figure N` wiki pages are created.
2. Every new entity's type is one of the 7 vocabulary values.
3. Formulas on wiki pages render via KaTeX (no broken-image icons).
4. Dangling `[[links]]` still render with the dotted `?unresolved` style, and their names are canonical concept names rather than sentence fragments.

This step requires LLM credentials and a live Postgres — it is the acceptance gate from the spec, not part of the automated suite.

---

## Out of scope (phase 2 — do NOT implement)

- Enrichment of dangling links (wiki search / web search / LLM / human editing)
- Aggregating all mentions as wiki-page generation input
- Bulk re-cleaning of already-ingested `content_text` / wiki pages (re-ingest covers it case-by-case)
- `CONTEXTUAL_PREFIX_PROMPT` (chunk contextualization) changes
