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

_IMAGE_RE = re.compile(r"!\[(?P<alt>.*?)\]\((?P<path>[^)]*)\)")
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
