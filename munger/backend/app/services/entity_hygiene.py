"""Extraction-time entity hygiene — drop obvious non-entities at the source.

Local, recall-safe filtering only (numbers, dataset trace labels, too-short). Importance
pruning is a *global* judgment and belongs to the salience gate / a separate improve
pipeline, not here.
"""

from __future__ import annotations

import re

# Dataset trace labels seen in traffic papers: AUG89.LB, FEB92.MP, 0CT89.HP, ...
_TRACE_LABEL_RE = re.compile(r"^[A-Za-z0-9]{2,8}\.(LB|HB|MP|LP|HP)$", re.IGNORECASE)


def is_low_value_entity_name(name: str) -> bool:
    """True for names that are clearly not real entities.

    Drops: too-short (<2 chars), names with no letter at all (pure numbers, decimals,
    percentages, ratios), and dataset trace labels. Keeps short real acronyms (RED, AQM)
    and digit-containing concepts (1/f noise, B-ISDN, 27 consecutive hours).
    """
    n = (name or "").strip()
    if len(n) < 2:
        return True
    if not any(c.isalpha() for c in n):
        return True
    if _TRACE_LABEL_RE.match(n):
        return True
    return False
