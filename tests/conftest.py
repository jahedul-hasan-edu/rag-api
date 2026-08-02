"""
Shared pytest fixtures.

Environment variables are set before Settings / app import so BaseSettings
can construct without a real .env file.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

# Must be set before importing application modules that call get_settings().
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://test:test@localhost:5432/test_rag",
)
os.environ.setdefault("OPENAI_API_KEY", "sk-test-key-not-real")
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("LOG_LEVEL", "WARNING")
os.environ.setdefault("APP_VERSION", "0.1.0-test")
os.environ.setdefault("LOAD_EMBEDDING_MODEL_ON_STARTUP", "false")
os.environ.setdefault("MAX_UPLOAD_SIZE_BYTES", "1048576")


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def fake_embedding_provider():
    """Deterministic EmbeddingProvider that never loads sentence-transformers."""
    from app.rag.embedding.base import EmbeddingProvider

    class FakeEmbeddingProvider(EmbeddingProvider):
        def __init__(self) -> None:
            self._ready = True

        @property
        def model_name(self) -> str:
            return "fake-bge-test"

        @property
        def dimension(self) -> int:
            return 384

        def is_ready(self) -> bool:
            return self._ready

        def load(self) -> None:
            self._ready = True

        def embed(self, texts: list[str]) -> list[list[float]]:
            return [[float((i + j) % 17) / 17.0 for j in range(384)] for i, _ in enumerate(texts)]

    return FakeEmbeddingProvider()


@pytest.fixture
async def app(fake_embedding_provider) -> AsyncIterator[FastAPI]:
    """Application instance with DB engine mocked and embeddings faked."""
    from app.core.config import get_settings
    from app.core.dependencies import get_embedding_provider

    get_settings.cache_clear()

    mock_conn = AsyncMock()
    mock_conn.execute = AsyncMock(return_value=None)
    mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_conn.__aexit__ = AsyncMock(return_value=None)

    mock_engine = MagicMock()
    mock_engine.connect = MagicMock(return_value=mock_conn)
    mock_engine.dispose = AsyncMock()

    with patch("app.db.database.create_engine", return_value=mock_engine):
        with patch("app.api.v1.health.get_engine", return_value=mock_engine):
            from main import create_app

            application = create_app()
            application.dependency_overrides[get_embedding_provider] = (
                lambda: fake_embedding_provider
            )
            yield application
            application.dependency_overrides.clear()

    get_settings.cache_clear()


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    """ASGI test client bound to the shared app fixture."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
