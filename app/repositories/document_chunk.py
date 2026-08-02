"""
SQLAlchemy implementations of repository interfaces.

Repositories only perform data access — no business rules.
"""

from __future__ import annotations

import uuid
from typing import Sequence

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import DocumentChunk
from app.repositories.interfaces import DocumentChunkRepository


class SqlAlchemyDocumentChunkRepository(DocumentChunkRepository):
    """Async SQLAlchemy-backed DocumentChunk repository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, chunk_id: uuid.UUID) -> DocumentChunk | None:
        result = await self._session.execute(
            select(DocumentChunk).where(DocumentChunk.id == chunk_id)
        )
        return result.scalar_one_or_none()

    async def list_by_document_id(
        self,
        document_id: uuid.UUID,
    ) -> Sequence[DocumentChunk]:
        result = await self._session.execute(
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index.asc())
        )
        return result.scalars().all()

    async def add(self, chunk: DocumentChunk) -> DocumentChunk:
        self._session.add(chunk)
        await self._session.flush()
        await self._session.refresh(chunk)
        return chunk

    async def add_many(self, chunks: Sequence[DocumentChunk]) -> Sequence[DocumentChunk]:
        if not chunks:
            return []
        self._session.add_all(list(chunks))
        await self._session.flush()
        for chunk in chunks:
            await self._session.refresh(chunk)
        return chunks

    async def delete_by_document_id(self, document_id: uuid.UUID) -> int:
        result = await self._session.execute(
            delete(DocumentChunk).where(DocumentChunk.document_id == document_id)
        )
        return int(result.rowcount or 0)
