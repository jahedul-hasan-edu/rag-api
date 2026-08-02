"""Text normalization helpers shared by all extractors."""

from __future__ import annotations

import re

_EXCESSIVE_BLANK_LINES = re.compile(r"\n{3,}")
_TRAILING_SPACES = re.compile(r"[ \t]+\n")
_MULTIPLE_SPACES = re.compile(r"[ \t]{2,}")


def normalize_text(text: str) -> str:
    """
    Normalize extracted text while preserving paragraph boundaries.

    - Convert CRLF / CR to LF
    - Strip trailing whitespace on each line
    - Collapse runs of spaces/tabs within a line
    - Collapse 3+ consecutive blank lines to a single paragraph break
    - Strip leading/trailing whitespace on the whole document
    """
    if not text:
        return ""

    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    normalized = _TRAILING_SPACES.sub("\n", normalized)
    normalized = _MULTIPLE_SPACES.sub(" ", normalized)
    normalized = _EXCESSIVE_BLANK_LINES.sub("\n\n", normalized)
    return normalized.strip()
