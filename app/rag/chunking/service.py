"""
Token-aware document chunking.

Independent of extraction and embedding: consumes ExtractedDocument and
returns plain Chunk dataclasses.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import tiktoken

from app.core.logging import get_logger
from app.rag.extraction.base import ExtractedDocument

logger = get_logger(__name__)

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")
_DEFAULT_ENCODING = "cl100k_base"


@dataclass(frozen=True, slots=True)
class Chunk:
    """A token-bounded slice of document text."""

    content: str
    page_number: int | None
    chunk_index: int
    token_count: int


class ChunkingService:
    """
    Split extracted documents into overlapping token windows.

    Prefers paragraph boundaries, then sentence boundaries, then hard cuts.
    """

    def __init__(
        self,
        *,
        chunk_size: int = 500,
        chunk_overlap: int = 100,
        encoding_name: str = _DEFAULT_ENCODING,
    ) -> None:
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        if chunk_overlap < 0:
            raise ValueError("chunk_overlap must be non-negative")
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be smaller than chunk_size")

        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap
        self._encoding = tiktoken.get_encoding(encoding_name)

    def count_tokens(self, text: str) -> int:
        """Return the token count for *text*."""
        return len(self._encoding.encode(text))

    def chunk_document(self, document: ExtractedDocument) -> list[Chunk]:
        """Chunk every page of *document* into overlapping windows."""
        chunks: list[Chunk] = []
        index = 0

        for page in document.pages:
            if not page.text.strip():
                continue
            page_chunks = self._chunk_text(page.text, page_number=page.page_number)
            for content, token_count in page_chunks:
                chunks.append(
                    Chunk(
                        content=content,
                        page_number=page.page_number,
                        chunk_index=index,
                        token_count=token_count,
                    )
                )
                index += 1

        logger.info(
            "chunking_completed",
            total_chunks=len(chunks),
            chunk_size=self._chunk_size,
            chunk_overlap=self._chunk_overlap,
        )
        return chunks

    def _chunk_text(
        self,
        text: str,
        *,
        page_number: int,
    ) -> list[tuple[str, int]]:
        """Split a single page's text into (content, token_count) pairs."""
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
        if not paragraphs:
            return []

        units = self._units_from_paragraphs(paragraphs)
        if not units:
            return []

        results: list[tuple[str, int]] = []
        current_units: list[str] = []
        current_tokens = 0

        for unit in units:
            unit_tokens = self.count_tokens(unit)

            # Oversized unit: hard-split by tokens
            if unit_tokens > self._chunk_size:
                if current_units:
                    results.append(self._materialize(current_units))
                    current_units, current_tokens = self._overlap_seed(current_units)

                for piece in self._hard_split(unit):
                    results.append(piece)
                current_units, current_tokens = [], 0
                # Seed overlap from last hard piece
                if results:
                    last_content = results[-1][0]
                    current_units, current_tokens = self._overlap_from_text(last_content)
                continue

            separator_tokens = self.count_tokens(" ") if current_units else 0
            projected = current_tokens + separator_tokens + unit_tokens

            if projected <= self._chunk_size:
                current_units.append(unit)
                current_tokens = projected
                continue

            if current_units:
                results.append(self._materialize(current_units))
                current_units, current_tokens = self._overlap_seed(current_units)

            separator_tokens = self.count_tokens(" ") if current_units else 0
            projected = current_tokens + separator_tokens + unit_tokens
            if projected <= self._chunk_size:
                current_units.append(unit)
                current_tokens = projected
            else:
                # Overlap seed already filled the window — start fresh
                current_units = [unit]
                current_tokens = unit_tokens

        if current_units:
            results.append(self._materialize(current_units))

        logger.debug(
            "page_chunked",
            page_number=page_number,
            chunks=len(results),
        )
        return results

    def _units_from_paragraphs(self, paragraphs: list[str]) -> list[str]:
        """Expand paragraphs into sentence-sized units when needed."""
        units: list[str] = []
        for paragraph in paragraphs:
            token_count = self.count_tokens(paragraph)
            if token_count <= self._chunk_size:
                units.append(paragraph)
                continue
            sentences = [s.strip() for s in _SENTENCE_SPLIT.split(paragraph) if s.strip()]
            if len(sentences) <= 1:
                units.append(paragraph)
            else:
                units.extend(sentences)
        return units

    def _materialize(self, units: list[str]) -> tuple[str, int]:
        content = " ".join(units).strip()
        return content, self.count_tokens(content)

    def _overlap_seed(self, units: list[str]) -> tuple[list[str], int]:
        """Build the next window's starting units from the previous window's tail."""
        if self._chunk_overlap == 0 or not units:
            return [], 0

        seed: list[str] = []
        tokens = 0
        for unit in reversed(units):
            unit_tokens = self.count_tokens(unit)
            separator = self.count_tokens(" ") if seed else 0
            if tokens + separator + unit_tokens > self._chunk_overlap and seed:
                break
            seed.insert(0, unit)
            tokens = tokens + separator + unit_tokens
        return seed, tokens

    def _overlap_from_text(self, text: str) -> tuple[list[str], int]:
        """Approximate overlap after a hard split using trailing tokens."""
        if self._chunk_overlap == 0 or not text:
            return [], 0
        token_ids = self._encoding.encode(text)
        overlap_ids = token_ids[-self._chunk_overlap :]
        overlap_text = self._encoding.decode(overlap_ids).strip()
        if not overlap_text:
            return [], 0
        return [overlap_text], len(overlap_ids)

    def _hard_split(self, text: str) -> list[tuple[str, int]]:
        """Force-split text into chunk_size token windows with overlap."""
        token_ids = self._encoding.encode(text)
        if not token_ids:
            return []

        pieces: list[tuple[str, int]] = []
        step = max(self._chunk_size - self._chunk_overlap, 1)
        start = 0
        while start < len(token_ids):
            window = token_ids[start : start + self._chunk_size]
            content = self._encoding.decode(window).strip()
            if content:
                pieces.append((content, len(window)))
            if start + self._chunk_size >= len(token_ids):
                break
            start += step
        return pieces
