"""SQLAlchemy Document repository."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Document
from app.repositories.interfaces import DocumentRepository


class SqlAlchemyDocumentRepository(DocumentRepository):
    """Async SQLAlchemy-backed Document repository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, document_id: uuid.UUID) -> Document | None:
        result = await self._session.execute(
            select(Document).where(Document.id == document_id)
        )
        return result.scalar_one_or_none()

    async def get_by_sha256(self, sha256_hash: str) -> Document | None:
        result = await self._session.execute(
            select(Document).where(Document.sha256_hash == sha256_hash)
        )
        return result.scalar_one_or_none()

    async def add(self, document: Document) -> Document:
        self._session.add(document)
        await self._session.flush()
        await self._session.refresh(document)
        return document
