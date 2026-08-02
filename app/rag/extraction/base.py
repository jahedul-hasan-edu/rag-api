"""
Document extraction domain types and abstract interface.

Extractors only turn bytes into normalized text + page metadata.
They never generate embeddings or touch persistence.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class ExtractedPage:
    """Text content belonging to a single logical page."""

    page_number: int
    text: str


@dataclass(frozen=True, slots=True)
class ExtractedDocument:
    """Result of extracting text from an uploaded file."""

    pages: tuple[ExtractedPage, ...]
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def text(self) -> str:
        """Full document text joined with blank lines between pages."""
        return "\n\n".join(page.text for page in self.pages if page.text)

    @property
    def total_pages(self) -> int:
        """Number of logical pages returned by the extractor."""
        return len(self.pages)


class DocumentExtractor(ABC):
    """Port for format-specific text extractors."""

    @abstractmethod
    def extract(self, file_bytes: bytes, *, filename: str) -> ExtractedDocument:
        """
        Extract and normalize text from *file_bytes*.

        Raises:
            CorruptedFileError: when the file cannot be parsed.
            ExtractionError: for unexpected extraction failures.
        """
