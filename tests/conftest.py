"""
Shared pytest fixtures.

Environment variables are set before Settings / app import so BaseSettings
can construct without a real .env file.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator, Iterator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
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


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    """ASGI test client with lifespan, DB connect mocked as healthy."""
    from app.core.config import get_settings

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
            transport = ASGITransport(app=application)
            async with AsyncClient(
                transport=transport,
                base_url="http://test",
            ) as ac:
                yield ac

    get_settings.cache_clear()
