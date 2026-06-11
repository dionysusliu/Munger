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
