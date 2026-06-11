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

_FALLBACK_PROMPT = "Create a well-structured wiki page."


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
