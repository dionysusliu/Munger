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
