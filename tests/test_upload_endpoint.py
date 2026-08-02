"""Upload endpoint HTTP tests."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from app.core.dependencies import get_upload_service
from app.core.exceptions import (
    CorruptedFileError,
    EmptyFileError,
    FileTooLargeError,
    UnsupportedFileError,
)
from app.services.upload import UploadResult


@pytest.mark.asyncio
async def test_upload_endpoint_success(app: FastAPI, client: AsyncClient) -> None:
    mock_service = AsyncMock()
    mock_service.process = AsyncMock(
        return_value=UploadResult(
            document_id=uuid.uuid4(),
            filename="notes.txt",
            total_pages=1,
            total_chunks=2,
            embedding_model="fake-bge-test",
            processing_time=0.12,
            status="completed",
        )
    )
    app.dependency_overrides[get_upload_service] = lambda: mock_service
    response = await client.post(
        "/api/v1/upload",
        files={"file": ("notes.txt", b"hello world", "text/plain")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["filename"] == "notes.txt"
    assert payload["total_chunks"] == 2
    assert payload["status"] == "completed"
    mock_service.process.assert_awaited_once()


@pytest.mark.asyncio
async def test_upload_endpoint_unsupported_file(app: FastAPI, client: AsyncClient) -> None:
    mock_service = AsyncMock()
    mock_service.process = AsyncMock(
        side_effect=UnsupportedFileError("Unsupported file type '.csv'.")
    )
    app.dependency_overrides[get_upload_service] = lambda: mock_service
    response = await client.post(
        "/api/v1/upload",
        files={"file": ("data.csv", b"a,b", "text/csv")},
    )

    assert response.status_code == 400
    assert response.json()["error"] == "unsupported_file"


@pytest.mark.asyncio
async def test_upload_endpoint_file_too_large(app: FastAPI, client: AsyncClient) -> None:
    mock_service = AsyncMock()
    mock_service.process = AsyncMock(
        side_effect=FileTooLargeError("File exceeds maximum upload size of 1024 bytes.")
    )
    app.dependency_overrides[get_upload_service] = lambda: mock_service
    response = await client.post(
        "/api/v1/upload",
        files={"file": ("big.txt", b"x" * 100, "text/plain")},
    )

    assert response.status_code == 413
    assert response.json()["error"] == "file_too_large"


@pytest.mark.asyncio
async def test_upload_endpoint_empty_file(app: FastAPI, client: AsyncClient) -> None:
    mock_service = AsyncMock()
    mock_service.process = AsyncMock(side_effect=EmptyFileError())
    app.dependency_overrides[get_upload_service] = lambda: mock_service
    response = await client.post(
        "/api/v1/upload",
        files={"file": ("empty.txt", b"", "text/plain")},
    )

    assert response.status_code == 422
    assert response.json()["error"] == "empty_file"


@pytest.mark.asyncio
async def test_upload_endpoint_corrupted_file(app: FastAPI, client: AsyncClient) -> None:
    mock_service = AsyncMock()
    mock_service.process = AsyncMock(
        side_effect=CorruptedFileError("PDF file is corrupted or unreadable.")
    )
    app.dependency_overrides[get_upload_service] = lambda: mock_service
    response = await client.post(
        "/api/v1/upload",
        files={"file": ("broken.pdf", b"%PDF-bad", "application/pdf")},
    )

    assert response.status_code == 422
    assert response.json()["error"] == "corrupted_file"
