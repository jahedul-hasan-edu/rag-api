"""
Repository interfaces (ports).

Concrete implementations live alongside these ABCs so services depend on
abstractions, not SQLAlchemy sessions directly.
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from typing import Sequence

from app.db.models import Conversation, Document, DocumentChunk, Message


class DocumentRepository(ABC):
    """Persistence port for Document aggregates."""

    @abstractmethod
    async def get_by_id(self, document_id: uuid.UUID) -> Document | None:
        """Return a document by primary key, or None if missing."""

    @abstractmethod
    async def get_by_sha256(self, sha256_hash: str) -> Document | None:
        """Return a document matching the content hash, or None."""

    @abstractmethod
    async def add(self, document: Document) -> Document:
        """Persist a new document and return it."""


class DocumentChunkRepository(ABC):
    """Persistence port for DocumentChunk aggregates."""

    @abstractmethod
    async def get_by_id(self, chunk_id: uuid.UUID) -> DocumentChunk | None:
        """Return a chunk by primary key, or None if missing."""

    @abstractmethod
    async def list_by_document_id(
        self,
        document_id: uuid.UUID,
    ) -> Sequence[DocumentChunk]:
        """Return all chunks for a document ordered by chunk_index."""

    @abstractmethod
    async def add(self, chunk: DocumentChunk) -> DocumentChunk:
        """Persist a new chunk and return it."""

    @abstractmethod
    async def add_many(self, chunks: Sequence[DocumentChunk]) -> Sequence[DocumentChunk]:
        """Persist many chunks in one flush and return them."""

    @abstractmethod
    async def delete_by_document_id(self, document_id: uuid.UUID) -> int:
        """Delete all chunks for a document; return rows deleted."""


class ConversationRepository(ABC):
    """Persistence port for Conversation aggregates."""

    @abstractmethod
    async def get_by_id(self, conversation_id: uuid.UUID) -> Conversation | None:
        """Return a conversation by id, or None."""

    @abstractmethod
    async def add(self, conversation: Conversation) -> Conversation:
        """Persist a new conversation."""

    @abstractmethod
    async def touch(self, conversation: Conversation) -> Conversation:
        """Bump updated_at and flush."""


class MessageRepository(ABC):
    """Persistence port for Message aggregates."""

    @abstractmethod
    async def list_by_conversation_id(
        self,
        conversation_id: uuid.UUID,
        *,
        limit: int | None = None,
    ) -> Sequence[Message]:
        """Return messages ordered by created_at ascending (optionally last *limit*)."""

    @abstractmethod
    async def add(self, message: Message) -> Message:
        """Persist a new message."""

    @abstractmethod
    async def add_many(self, messages: Sequence[Message]) -> Sequence[Message]:
        """Persist many messages."""
