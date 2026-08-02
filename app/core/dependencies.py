"""
FastAPI dependency injection wiring.

Keeps constructors at the edge of the app so routers/services stay thin
and testable.
"""

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.rag.chunking import ChunkingService
from app.rag.embedding import EmbeddingProvider, LocalBGEEmbeddingProvider
from app.repositories.document import SqlAlchemyDocumentRepository
from app.repositories.document_chunk import SqlAlchemyDocumentChunkRepository
from app.repositories.interfaces import DocumentChunkRepository, DocumentRepository
from app.services.upload import UploadService

SettingsDep = Annotated[Settings, Depends(get_settings)]
DbSessionDep = Annotated[AsyncSession, Depends(get_db)]


async def get_document_repository(
    session: DbSessionDep,
) -> AsyncGenerator[DocumentRepository, None]:
    """Provide a DocumentRepository bound to the request session."""
    yield SqlAlchemyDocumentRepository(session)


async def get_document_chunk_repository(
    session: DbSessionDep,
) -> AsyncGenerator[DocumentChunkRepository, None]:
    """Provide a DocumentChunkRepository bound to the request session."""
    yield SqlAlchemyDocumentChunkRepository(session)


def get_embedding_provider(request: Request) -> EmbeddingProvider:
    """
    Resolve the process-wide embedding provider.

    Prefer the instance attached during lifespan; fall back to the singleton
    so unit tests can override via app.dependency_overrides.
    """
    provider = getattr(request.app.state, "embedding_provider", None)
    if provider is not None:
        return provider  # type: ignore[no-any-return]
    settings = get_settings()
    return LocalBGEEmbeddingProvider.get_instance(
        model_name=settings.embedding_model_name,
        dimension=settings.embedding_dimension,
        batch_size=settings.embedding_batch_size,
    )


def get_chunking_service(settings: SettingsDep) -> ChunkingService:
    """Build a ChunkingService from application settings."""
    return ChunkingService(
        chunk_size=settings.chunk_size_tokens,
        chunk_overlap=settings.chunk_overlap_tokens,
    )


async def get_upload_service(
    settings: SettingsDep,
    document_repository: Annotated[
        DocumentRepository,
        Depends(get_document_repository),
    ],
    chunk_repository: Annotated[
        DocumentChunkRepository,
        Depends(get_document_chunk_repository),
    ],
    chunking_service: Annotated[ChunkingService, Depends(get_chunking_service)],
    embedding_provider: Annotated[EmbeddingProvider, Depends(get_embedding_provider)],
) -> UploadService:
    """Assemble UploadService with request-scoped collaborators."""
    return UploadService(
        settings=settings,
        document_repository=document_repository,
        chunk_repository=chunk_repository,
        chunking_service=chunking_service,
        embedding_provider=embedding_provider,
    )


DocumentRepoDep = Annotated[DocumentRepository, Depends(get_document_repository)]
DocumentChunkRepoDep = Annotated[
    DocumentChunkRepository,
    Depends(get_document_chunk_repository),
]
EmbeddingProviderDep = Annotated[EmbeddingProvider, Depends(get_embedding_provider)]
UploadServiceDep = Annotated[UploadService, Depends(get_upload_service)]
