"""Chat API tests (SSE + history)."""

from __future__ import annotations

import json
import uuid
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from app.core.dependencies import get_chat_service
from app.core.exceptions import ConversationNotFoundError
from app.db.models import Conversation, Message
from app.services.rag_pipeline import format_sse


class FakeChatService:
    def __init__(self) -> None:
        self.conversation_id = uuid.uuid4()

    async def stream_chat(
        self,
        *,
        question: str,
        conversation_id=None,
        filters=None,
    ) -> AsyncIterator[str]:
        cid = conversation_id or self.conversation_id
        yield format_sse("conversation", {"conversation_id": str(cid)})
        yield format_sse("token", {"token": "Answer"})
        yield format_sse(
            "done",
            {
                "conversation_id": str(cid),
                "answer": "Answer",
                "citations": [],
                "retrieved_chunk_count": 0,
                "processing_time": 0.02,
            },
        )

    async def get_conversation(self, conversation_id: uuid.UUID) -> Conversation:
        now = datetime.now(timezone.utc)
        conversation = Conversation(
            id=conversation_id,
            title="Test",
            created_at=now,
            updated_at=now,
        )
        conversation.messages = [
            Message(
                id=uuid.uuid4(),
                conversation_id=conversation_id,
                role="user",
                content="Hello?",
                retrieved_chunk_ids=[],
                citations=[],
                created_at=now,
            ),
            Message(
                id=uuid.uuid4(),
                conversation_id=conversation_id,
                role="assistant",
                content="Hi there.",
                retrieved_chunk_ids=[],
                citations=[],
                created_at=now,
            ),
        ]
        return conversation


def _parse_sse(raw: str) -> list[tuple[str, dict]]:
    events: list[tuple[str, dict]] = []
    for block in [b for b in raw.split("\n\n") if b.strip()]:
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
async def test_chat_endpoint_streams_sse(app: FastAPI, client: AsyncClient) -> None:
    service = FakeChatService()
    app.dependency_overrides[get_chat_service] = lambda: service
    response = await client.post("/api/v1/chat", json={"question": "Hello?"})
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    events = _parse_sse(response.text)
    assert events[0][0] == "conversation"
    assert events[0][1]["conversation_id"] == str(service.conversation_id)
    assert events[-1][0] == "done"
    assert events[-1][1]["answer"] == "Answer"


@pytest.mark.asyncio
async def test_get_conversation(app: FastAPI, client: AsyncClient) -> None:
    service = FakeChatService()
    app.dependency_overrides[get_chat_service] = lambda: service
    cid = service.conversation_id
    response = await client.get(f"/api/v1/chat/{cid}")
    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == str(cid)
    assert len(payload["messages"]) == 2
    assert payload["messages"][0]["role"] == "user"
    assert payload["messages"][1]["content"] == "Hi there."


@pytest.mark.asyncio
async def test_get_conversation_not_found(app: FastAPI, client: AsyncClient) -> None:
    missing = uuid.uuid4()

    class MissingChatService(FakeChatService):
        async def get_conversation(self, conversation_id: uuid.UUID) -> Conversation:
            raise ConversationNotFoundError(conversation_id)

    app.dependency_overrides[get_chat_service] = lambda: MissingChatService()
    response = await client.get(f"/api/v1/chat/{missing}")
    assert response.status_code == 404
    assert response.json()["error"] == "conversation_not_found"
