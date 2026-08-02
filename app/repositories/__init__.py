"""Data access repositories."""

from app.repositories.document_chunk import SqlAlchemyDocumentChunkRepository
from app.repositories.interfaces import DocumentChunkRepository

__all__ = [
    "DocumentChunkRepository",
    "SqlAlchemyDocumentChunkRepository",
]
