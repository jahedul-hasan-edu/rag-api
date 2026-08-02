"""
FastAPI dependency injection wiring.

Keeps constructors at the edge of the app so routers/services stay thin
and testable.
"""

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.repositories.document_chunk import SqlAlchemyDocumentChunkRepository
from app.repositories.interfaces import DocumentChunkRepository

SettingsDep = Annotated[Settings, Depends(get_settings)]
DbSessionDep = Annotated[AsyncSession, Depends(get_db)]


async def get_document_chunk_repository(
    session: DbSessionDep,
) -> AsyncGenerator[DocumentChunkRepository, None]:
    """Provide a DocumentChunkRepository bound to the request session."""
    yield SqlAlchemyDocumentChunkRepository(session)


DocumentChunkRepoDep = Annotated[
    DocumentChunkRepository,
    Depends(get_document_chunk_repository),
]
