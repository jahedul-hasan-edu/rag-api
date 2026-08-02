"""
Retrieval domain types and ports.

Designed so hybrid search, reranking, and alternate embedding models can be
added behind the same Retriever interface without changing services.
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Sequence


@dataclass(frozen=True, slots=True)
class RetrievalFilters:
    """Optional metadata filters applied during retrieval."""

    document_id: uuid.UUID | None = None
    filename: str | None = None
    tags: tuple[str, ...] = ()
    page_number: int | None = None


@dataclass(frozen=True, slots=True)
class RetrievedChunk:
    """A chunk returned by semantic (or future hybrid) retrieval."""

    chunk_id: uuid.UUID
    document_id: uuid.UUID
    content: str
    similarity_score: float
    page_number: int | None
    chunk_index: int
    filename: str
    metadata: dict[str, Any] = field(default_factory=dict)


class Retriever(ABC):
    """Port for document chunk retrieval strategies."""

    @abstractmethod
    async def retrieve(
        self,
        query_embedding: list[float],
        *,
        top_k: int = 5,
        filters: RetrievalFilters | None = None,
    ) -> Sequence[RetrievedChunk]:
        """Return the top-*k* chunks ranked by relevance to *query_embedding*."""
