"""Text processing utilities for Munger."""
import re
import hashlib
from typing import List


def extract_markdown_links(content: str) -> List[str]:
    """Extract all [[wiki link]] and [markdown](link) references from content."""
    if not content:
        return []

    # [[Wiki Link]] style
    wiki_links = re.findall(r'\[\[([^\]]+)\]\]', content)

    # [text](url) style
    md_links = re.findall(r'\[([^\]]*)\]\(([^)]+)\)', content)
    md_urls = [url for _, url in md_links]

    return list(set(wiki_links + md_urls))


def generate_slug(title: str) -> str:
    """Generate a URL-friendly slug from a title."""
    if not title:
        return "untitled"

    # Convert to lowercase
    slug = title.lower()

    # Replace spaces and underscores with hyphens
    slug = re.sub(r'[\s_]+', '-', slug)

    # Remove non-alphanumeric characters except hyphens
    slug = re.sub(r'[^a-z0-9\-]', '', slug)

    # Collapse multiple hyphens
    slug = re.sub(r'-+', '-', slug)

    # Strip leading/trailing hyphens
    slug = slug.strip('-')

    # Ensure not empty
    if not slug:
        hash_suffix = hashlib.md5(title.encode()).hexdigest()[:8]
        return f"untitled-{hash_suffix}"

    return slug


def truncate_text(text: str, max_length: int = 500) -> str:
    """Truncate text to max_length, preserving word boundaries."""
    if not text or len(text) <= max_length:
        return text or ""

    # Find the last space before max_length
    truncated = text[:max_length]
    last_space = truncated.rfind(' ')

    if last_space > max_length * 0.8:
        truncated = truncated[:last_space]

    return truncated + "..."


def count_words(text: str) -> int:
    """Count words in text."""
    if not text:
        return 0

    # Split on whitespace and filter empty strings
    words = [w for w in text.split() if w.strip()]
    return len(words)


def chunk_text(text: str, chunk_size: int = 2000, overlap: int = 200) -> List[str]:
    """Split text into overlapping chunks, respecting paragraph boundaries."""
    if not text:
        return []

    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0

    while start < len(text):
        # Determine the end of this chunk
        end = start + chunk_size

        if end >= len(text):
            # Last chunk
            chunks.append(text[start:])
            break

        # Try to find a paragraph break near the end
        chunk = text[start:end]

        # Look for the last paragraph break before the chunk end
        para_break = chunk.rfind('\n\n')
        if para_break > chunk_size * 0.7:
            end = start + para_break + 2
        else:
            # Fall back to the last sentence break
            sentence_break = max(
                chunk.rfind('. '),
                chunk.rfind('? '),
                chunk.rfind('! ')
            )
            if sentence_break > chunk_size * 0.7:
                end = start + sentence_break + 2
            else:
                # Fall back to the last space
                last_space = chunk.rfind(' ')
                if last_space > chunk_size * 0.8:
                    end = start + last_space

        chunks.append(text[start:end].strip())

        # Move start forward by chunk_size minus overlap
        start = end - overlap

    return chunks
