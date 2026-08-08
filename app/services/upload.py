"""
Upload / ingestion orchestration.

All pipeline steps live here so the same service can later run under
Celery, RQ, Dramatiq, or FastAPI BackgroundTasks without changing
business logic. Routers only validate the HTTP envelope and call process().
"""

from __future__ import annotations

import asyncio
import hashlib
import time
import uuid
from dataclasses import dataclass
from typing import Literal

from app.core.config import Settings
from app.core.exceptions import (
    AppError,
    DatabaseUnavailableError,
    EmptyFileError,
    FileTooLargeError,
    ProcessingError,
    UnsupportedFileError,
)
from app.core.logging import get_logger
from app.db.models import Document, DocumentChunk
from app.rag.chunking import ChunkingService
from app.rag.embedding import EmbeddingProvider
from app.rag.extraction import get_extractor, resolve_mime_type
from app.repositories.interfaces import DocumentChunkRepository, DocumentRepository

logger = get_logger(__name__)

UploadStatus = Literal["completed", "duplicate"]

_DB_CONNECTION_MARKERS = (
    "getaddrinfo failed",
    "gaierror",
    "could not translate host name",
    "connection refused",
    "timeout expired",
    "connection reset",
    "server closed the connection",
    "password authentication failed",
    "could not connect to server",
    "name or service not known",
    "nodename nor servname provided",
)


def _is_database_connectivity_error(exc: BaseException) -> bool:
    """Return True for typical DNS / network / auth failures talking to Postgres."""
    text = str(exc).lower()
    if any(marker in text for marker in _DB_CONNECTION_MARKERS):
        return True
    cause = getattr(exc, "__cause__", None) or getattr(exc, "orig", None)
    if cause is not None and cause is not exc:
        return _is_database_connectivity_error(cause)
    return False


@dataclass(frozen=True, slots=True)
class UploadResult:
    """Outcome of the document ingestion pipeline."""

    document_id: uuid.UUID
    filename: str
    total_pages: int
    total_chunks: int
    embedding_model: str
    processing_time: float
    status: UploadStatus


class UploadService:
    """
    Coordinate validate → extract → chunk → embed → persist.

    Designed as a plain callable use-case object (no FastAPI imports) so
    background workers can invoke the same process() method later.
    """

    def __init__(
        self,
        *,
        settings: Settings,
        document_repository: DocumentRepository,
        chunk_repository: DocumentChunkRepository,
        chunking_service: ChunkingService,
        embedding_provider: EmbeddingProvider,
    ) -> None:
        self._settings = settings
        self._documents = document_repository
        self._chunks = chunk_repository
        self._chunking = chunking_service
        self._embeddings = embedding_provider

    async def process(self, *, filename: str, file_bytes: bytes) -> UploadResult:
        """
        Run the full ingestion pipeline for one uploaded file.

        Persistence uses the injected session repositories; the request-scoped
        session commits on success and rolls back on any exception.
        """
        started = time.perf_counter()
        logger.info("upload_started", filename=filename, size_bytes=len(file_bytes))

        try:
            self._validate(filename=filename, file_bytes=file_bytes)
            logger.info("validation_completed", filename=filename)

            sha256_hash = hashlib.sha256(file_bytes).hexdigest()
            existing = await self._documents.get_by_sha256(sha256_hash)
            if existing is not None:
                elapsed = time.perf_counter() - started
                logger.info(
                    "duplicate_detection",
                    filename=filename,
                    document_id=str(existing.id),
                    sha256_hash=sha256_hash,
                )
                return UploadResult(
                    document_id=existing.id,
                    filename=existing.filename,
                    total_pages=existing.total_pages,
                    total_chunks=existing.total_chunks,
                    embedding_model=existing.embedding_model,
                    processing_time=round(elapsed, 4),
                    status="duplicate",
                )

            mime_type = resolve_mime_type(filename)
            extractor = get_extractor(filename)
            extracted = await asyncio.to_thread(
                extractor.extract,
                file_bytes,
                filename=filename,
            )
            logger.info(
                "text_extraction_completed",
                filename=filename,
                total_pages=extracted.total_pages,
            )

            chunks = await asyncio.to_thread(self._chunking.chunk_document, extracted)
            logger.info("chunking_completed", filename=filename, total_chunks=len(chunks))

            if not chunks:
                # Persist an empty document record with zero chunks rather than failing
                # hard on whitespace-only files that passed empty-byte validation.
                embeddings: list[list[float]] = []
            else:
                texts = [chunk.content for chunk in chunks]
                embeddings = await asyncio.to_thread(self._embeddings.embed, texts)
                if len(embeddings) != len(chunks):
                    raise ProcessingError(
                        "Embedding provider returned an unexpected vector count.",
                        details={
                            "expected": len(chunks),
                            "received": len(embeddings),
                        },
                    )
                logger.info(
                    "embedding_completed",
                    filename=filename,
                    total_embeddings=len(embeddings),
                    model=self._embeddings.model_name,
                )

            document = Document(
                id=uuid.uuid4(),
                filename=filename,
                file_size=len(file_bytes),
                mime_type=mime_type,
                sha256_hash=sha256_hash,
                total_pages=extracted.total_pages,
                total_chunks=len(chunks),
                embedding_model=self._embeddings.model_name,
                metadata_={
                    **extracted.metadata,
                    "sha256_hash": sha256_hash,
                },
            )
            await self._documents.add(document)

            if chunks:
                chunk_models = [
                    DocumentChunk(
                        id=uuid.uuid4(),
                        document_id=document.id,
                        page_number=chunk.page_number,
                        chunk_index=chunk.chunk_index,
                        content=chunk.content,
                        token_count=chunk.token_count,
                        embedding=embeddings[i],
                        metadata_={
                            "filename": filename,
                            "embedding_model": self._embeddings.model_name,
                        },
                    )
                    for i, chunk in enumerate(chunks)
                ]
                await self._chunks.add_many(chunk_models)

            elapsed = time.perf_counter() - started
            logger.info(
                "database_insert_completed",
                document_id=str(document.id),
                total_chunks=len(chunks),
                processing_time=round(elapsed, 4),
            )
            return UploadResult(
                document_id=document.id,
                filename=document.filename,
                total_pages=document.total_pages,
                total_chunks=document.total_chunks,
                embedding_model=document.embedding_model,
                processing_time=round(elapsed, 4),
                status="completed",
            )
        except (UnsupportedFileError, FileTooLargeError, EmptyFileError):
            raise
        except Exception as exc:
            if isinstance(exc, AppError):
                logger.error(
                    "upload_failed",
                    filename=filename,
                    code=exc.code,
                    message=exc.message,
                )
                raise
            logger.exception("upload_failed", filename=filename, error=str(exc))
            if _is_database_connectivity_error(exc):
                raise DatabaseUnavailableError(
                    "Cannot reach the database. Check DATABASE_URL host/DNS "
                    "and that your Supabase project is active.",
                    details={"filename": filename, "reason": str(exc)},
                ) from exc
            raise ProcessingError(
                "Document processing failed.",
                details={"filename": filename, "reason": str(exc)},
            ) from exc

    def _validate(self, *, filename: str, file_bytes: bytes) -> None:
        if not filename or not filename.strip():
            raise UnsupportedFileError("Filename is required.")

        if len(file_bytes) == 0:
            raise EmptyFileError()

        max_size = self._settings.max_upload_size_bytes
        if len(file_bytes) > max_size:
            raise FileTooLargeError(
                f"File exceeds maximum upload size of {max_size} bytes.",
                details={
                    "filename": filename,
                    "size_bytes": len(file_bytes),
                    "max_upload_size_bytes": max_size,
                },
            )

        # Extension check (also done by extractor factory — fail fast here).
        resolve_mime_type(filename)
