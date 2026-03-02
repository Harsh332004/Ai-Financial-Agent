from __future__ import annotations

import re


def chunk_text(text: str, chunk_size: int = 300, chunk_overlap: int = 50) -> list[str]:
    """Split *text* into overlapping word-based chunks.

    Args:
        text: The full document text (already OCR-cleaned).
        chunk_size: Target number of words per chunk.
        chunk_overlap: Number of words to repeat at the start of the next chunk.

    Returns:
        A list of chunk strings.
    """
    text = _clean(text)
    words = text.split()

    if not words:
        return []

    chunks: list[str] = []
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        if end == len(words):
            break
        start += chunk_size - chunk_overlap

    return chunks


def _clean(text: str) -> str:
    """Light cleanup of OCR noise before chunking."""
    # Collapse multiple blank lines
    text = re.sub(r"\n{2,}", "\n", text)
    # Replace non-breaking spaces, tabs etc. with regular space
    text = re.sub(r"[^\S\n]+", " ", text)
    # Remove isolated single characters that are likely OCR artifacts
    text = re.sub(r"(?<!\w)\w(?!\w)", "", text)
    return text.strip()
