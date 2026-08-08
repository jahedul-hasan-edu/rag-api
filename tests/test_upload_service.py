"""UploadService unit tests with mocked collaborators."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.config import Settings
from app.core.exceptions import EmptyFileError, FileTooLargeError, UnsupportedFileError
from app.db.models import Document
from app.rag.chunking import Chunk, ChunkingService
from app.rag.extraction.base import ExtractedDocument, ExtractedPage
from app.services.upload import UploadService


@pytest.fixture
def settings() -> Settings:
    return Settings(
        DATABASE_URL="postgresql://postgres.pxiqdqgaqvkwqvrwpsea:12345@aws-1-us-east-1.pooler.supabase.com:5432/postgres",
        OPENAI_API_KEY="sk-test",
        MAX_UPLOAD_SIZE_BYTES=1024,
        LOAD_EMBEDDING_MODEL_ON_STARTUP=False,
    )


def _make_service(
    settings: Settings,
    *,
    existing: Document | None = None,
) -> tuple[UploadService, AsyncMock, AsyncMock, MagicMock, MagicMock]:
    documents = AsyncMock()
    documents.get_by_sha256 = AsyncMock(return_value=existing)
    documents.add = AsyncMock(side_effect=lambda doc: doc)

    chunks = AsyncMock()
    chunks.add_many = AsyncMock(side_effect=lambda items: items)

    chunking = MagicMock(spec=ChunkingService)
    chunking.chunk_document.return_value = [
        Chunk(content="hello world", page_number=1, chunk_index=0, token_count=2),
    ]

    embeddings = MagicMock()
    embeddings.model_name = "fake-bge"
    embeddings.embed.return_value = [[0.1] * 384]

    service = UploadService(
        settings=settings,
        document_repository=documents,
        chunk_repository=chunks,
        chunking_service=chunking,
        embedding_provider=embeddings,
    )
    return service, documents, chunks, chunking, embeddings


@pytest.mark.asyncio
async def test_upload_service_rejects_empty_file(settings: Settings) -> None:
    service, *_ = _make_service(settings)
    with pytest.raises(EmptyFileError):
        await service.process(filename="empty.txt", file_bytes=b"")


@pytest.mark.asyncio
async def test_upload_service_rejects_unsupported(settings: Settings) -> None:
    service, *_ = _make_service(settings)
    with pytest.raises(UnsupportedFileError):
        await service.process(filename="data.csv", file_bytes=b"a,b,c")


@pytest.mark.asyncio
async def test_upload_service_rejects_too_large(settings: Settings) -> None:
    service, *_ = _make_service(settings)
    with pytest.raises(FileTooLargeError):
        await service.process(filename="big.txt", file_bytes=b"x" * 2048)


@pytest.mark.asyncio
async def test_upload_service_returns_duplicate(settings: Settings) -> None:
    existing = Document(
        id=uuid.uuid4(),
        filename="notes.txt",
        file_size=11,
        mime_type="text/plain",
        sha256_hash="abc",
        total_pages=1,
        total_chunks=1,
        embedding_model="fake-bge",
    )
    service, documents, chunks, *_ = _make_service(settings, existing=existing)
    result = await service.process(filename="notes.txt", file_bytes=b"hello world")

    assert result.status == "duplicate"
    assert result.document_id == existing.id
    documents.add.assert_not_awaited()
    chunks.add_many.assert_not_awaited()


@pytest.mark.asyncio
async def test_upload_service_persists_new_document(
    settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, documents, chunks, chunking, embeddings = _make_service(settings)

    extracted = ExtractedDocument(
        pages=(ExtractedPage(page_number=1, text="hello world"),),
        metadata={"extractor": "TextExtractor"},
    )

    class FakeExtractor:
        def extract(self, file_bytes: bytes, *, filename: str) -> ExtractedDocument:
            return extracted

    monkeypatch.setattr("app.services.upload.get_extractor", lambda _fn: FakeExtractor())
    monkeypatch.setattr(
        "app.services.upload.resolve_mime_type",
        lambda _fn: "text/plain",
    )

    result = await service.process(filename="notes.txt", file_bytes=b"hello world")

    assert result.status == "completed"
    assert result.total_chunks == 1
    assert result.embedding_model == "fake-bge"
    documents.add.assert_awaited_once()
    chunks.add_many.assert_awaited_once()
    embeddings.embed.assert_called_once()
    chunking.chunk_document.assert_called_once()
