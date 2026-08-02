"""pgvector cosine-similarity retriever."""

from __future__ import annotations

import time
from typing import Sequence

from sqlalchemy import Select, Float, cast, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.models import Document, DocumentChunk
from app.rag.retrieval.base import RetrievedChunk, RetrievalFilters, Retriever

logger = get_logger(__name__)


class PgVectorRetriever(Retriever):
    """
    Cosine-similarity search over document_chunks.embedding.

    Uses pgvector's `<=>` distance operator; similarity = 1 - distance.
    Joins documents for filename / tag filters without coupling to services.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def retrieve(
        self,
        query_embedding: list[float],
        *,
        top_k: int = 5,
        filters: RetrievalFilters | None = None,
    ) -> Sequence[RetrievedChunk]:
        started = time.perf_counter()
        filters = filters or RetrievalFilters()

        distance = DocumentChunk.embedding.cosine_distance(query_embedding)
        similarity = (1 - distance).label("similarity_score")

        stmt: Select[Any] = (
            select(
                DocumentChunk.id,
                DocumentChunk.document_id,
                DocumentChunk.content,
                DocumentChunk.page_number,
                DocumentChunk.chunk_index,
                DocumentChunk.metadata_,
                Document.filename,
                similarity,
            )
            .join(Document, Document.id == DocumentChunk.document_id)
            .where(DocumentChunk.embedding.is_not(None))
            .order_by(distance.asc())
            .limit(top_k)
        )

        if filters.document_id is not None:
            stmt = stmt.where(DocumentChunk.document_id == filters.document_id)
        if filters.filename:
            stmt = stmt.where(Document.filename.ilike(filters.filename))
        if filters.page_number is not None:
            stmt = stmt.where(DocumentChunk.page_number == filters.page_number)
        for tag in filters.tags:
            # documents.metadata.tags JSON array contains tag
            stmt = stmt.where(Document.metadata_["tags"].contains([tag]))

        result = await self._session.execute(stmt)
        rows = result.all()

        chunks = [
            RetrievedChunk(
                chunk_id=row.id,
                document_id=row.document_id,
                content=row.content,
                similarity_score=float(row.similarity_score),
                page_number=row.page_number,
                chunk_index=row.chunk_index,
                filename=row.filename,
                metadata=dict(row.metadata_ or {}),
            )
            for row in rows
        ]

        elapsed_ms = (time.perf_counter() - started) * 1000
        logger.info(
            "vector_search_completed",
            retrieved_chunk_count=len(chunks),
            top_k=top_k,
            latency_ms=round(elapsed_ms, 2),
            document_id=str(filters.document_id) if filters.document_id else None,
        )
        return chunks


# Avoid importing typing.Any at module top for Select annotation clarity
from typing import Any  # noqa: E402
