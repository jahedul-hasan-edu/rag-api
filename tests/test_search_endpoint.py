"""Search SSE endpoint tests."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from app.core.dependencies import get_search_service
from app.services.rag_pipeline import format_sse


class FakeSearchService:
    async def stream_search(self, *, question: str, filters=None) -> AsyncIterator[str]:
        yield format_sse(
            "citation",
            {
                "chunk_id": "11111111-1111-1111-1111-111111111111",
                "document_id": "22222222-2222-2222-2222-222222222222",
                "filename": "notes.txt",
                "page_number": 1,
                "chunk_index": 0,
                "similarity_score": 0.91,
            },
        )
        yield format_sse("token", {"token": "Hello"})
        yield format_sse("token", {"token": " world"})
        yield format_sse(
            "done",
            {
                "answer": "Hello world",
                "citations": [],
                "retrieved_chunk_count": 1,
                "processing_time": 0.01,
            },
        )


def _parse_sse(raw: str) -> list[tuple[str, dict]]:
    events: list[tuple[str, dict]] = []
    blocks = [b for b in raw.split("\n\n") if b.strip()]
    for block in blocks:
        event = "message"
        data = ""
        for line in block.splitlines():
            if line.startswith("event:"):
                event = line.split(":", 1)[1].strip()
            elif line.startswith("data:"):
                data = line.split(":", 1)[1].strip()
        events.append((event, json.loads(data)))
    return events


@pytest.mark.asyncio
async def test_search_endpoint_streams_sse(app: FastAPI, client: AsyncClient) -> None:
    app.dependency_overrides[get_search_service] = lambda: FakeSearchService()
    response = await client.post(
        "/api/v1/search",
        json={"question": "What is in the notes?"},
    )
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    events = _parse_sse(response.text)
    names = [name for name, _ in events]
    assert names == ["citation", "token", "token", "done"]
    assert events[0][1]["filename"] == "notes.txt"
    assert events[1][1]["token"] == "Hello"
    assert events[-1][1]["answer"] == "Hello world"


@pytest.mark.asyncio
async def test_search_endpoint_validation_error(app: FastAPI, client: AsyncClient) -> None:
    app.dependency_overrides[get_search_service] = lambda: FakeSearchService()
    response = await client.post("/api/v1/search", json={"question": ""})
    assert response.status_code == 422
