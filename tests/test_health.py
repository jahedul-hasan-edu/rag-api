"""Health endpoint tests."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_returns_ok_when_database_connected(
    client: AsyncClient,
) -> None:
    """GET /health reports ok + connected when DB probe succeeds."""
    response = await client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["database"] == "connected"
    assert payload["environment"] == "development"
    assert payload["version"] == "0.1.0-test"
    assert "X-Request-ID" in response.headers
