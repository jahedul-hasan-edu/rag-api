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
from app.rag.llm import LLMProvider, OpenAILLMProvider
from app.rag.prompts import PromptBuilder
from app.rag.retrieval import PgVectorRetriever, Retriever
from app.repositories.conversation import (
    SqlAlchemyConversationRepository,
    SqlAlchemyMessageRepository,
)
from app.repositories.document import SqlAlchemyDocumentRepository
from app.repositories.document_chunk import SqlAlchemyDocumentChunkRepository
from app.repositories.interfaces import (
    ConversationRepository,
    DocumentChunkRepository,
    DocumentRepository,
    MessageRepository,
)
from app.services.chat import ChatService
from app.services.search import SearchService
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


async def get_conversation_repository(
    session: DbSessionDep,
) -> AsyncGenerator[ConversationRepository, None]:
    """Provide a ConversationRepository bound to the request session."""
    yield SqlAlchemyConversationRepository(session)


async def get_message_repository(
    session: DbSessionDep,
) -> AsyncGenerator[MessageRepository, None]:
    """Provide a MessageRepository bound to the request session."""
    yield SqlAlchemyMessageRepository(session)


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


def get_llm_provider(settings: SettingsDep) -> LLMProvider:
    """Build the OpenAI chat provider from settings."""
    return OpenAILLMProvider(
        api_key=settings.openai_api_key.get_secret_value(),
        model=settings.openai_model,
        temperature=settings.llm_temperature,
        base_url=settings.openai_base_url,
    )


def get_prompt_builder() -> PromptBuilder:
    """Return the shared grounded PromptBuilder."""
    return PromptBuilder()


async def get_retriever(session: DbSessionDep) -> AsyncGenerator[Retriever, None]:
    """Provide a pgvector Retriever bound to the request session."""
    yield PgVectorRetriever(session)


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


async def get_search_service(
    settings: SettingsDep,
    embedding_provider: Annotated[EmbeddingProvider, Depends(get_embedding_provider)],
    retriever: Annotated[Retriever, Depends(get_retriever)],
    prompt_builder: Annotated[PromptBuilder, Depends(get_prompt_builder)],
    llm_provider: Annotated[LLMProvider, Depends(get_llm_provider)],
) -> SearchService:
    """Assemble SearchService."""
    return SearchService(
        settings=settings,
        embedding_provider=embedding_provider,
        retriever=retriever,
        prompt_builder=prompt_builder,
        llm_provider=llm_provider,
    )


async def get_chat_service(
    settings: SettingsDep,
    conversation_repository: Annotated[
        ConversationRepository,
        Depends(get_conversation_repository),
    ],
    message_repository: Annotated[
        MessageRepository,
        Depends(get_message_repository),
    ],
    embedding_provider: Annotated[EmbeddingProvider, Depends(get_embedding_provider)],
    retriever: Annotated[Retriever, Depends(get_retriever)],
    prompt_builder: Annotated[PromptBuilder, Depends(get_prompt_builder)],
    llm_provider: Annotated[LLMProvider, Depends(get_llm_provider)],
) -> ChatService:
    """Assemble ChatService."""
    return ChatService(
        settings=settings,
        conversation_repository=conversation_repository,
        message_repository=message_repository,
        embedding_provider=embedding_provider,
        retriever=retriever,
        prompt_builder=prompt_builder,
        llm_provider=llm_provider,
    )


DocumentRepoDep = Annotated[DocumentRepository, Depends(get_document_repository)]
DocumentChunkRepoDep = Annotated[
    DocumentChunkRepository,
    Depends(get_document_chunk_repository),
]
EmbeddingProviderDep = Annotated[EmbeddingProvider, Depends(get_embedding_provider)]
UploadServiceDep = Annotated[UploadService, Depends(get_upload_service)]
SearchServiceDep = Annotated[SearchService, Depends(get_search_service)]
ChatServiceDep = Annotated[ChatService, Depends(get_chat_service)]
