"""SearchService streaming unit tests."""

from __future__ import annotations

import json
import uuid
from typing import Sequence
from unittest.mock import MagicMock

import pytest

from app.core.config import Settings
from app.rag.prompts import PromptBuilder
from app.rag.retrieval import RetrievedChunk, RetrievalFilters, Retriever
from app.services.search import SearchService


class FakeRetriever(Retriever):
    def __init__(self, chunks: Sequence[RetrievedChunk]) -> None:
        self.chunks = list(chunks)

    async def retrieve(
        self,
        query_embedding: list[float],
        *,
        top_k: int = 5,
        filters: RetrievalFilters | None = None,
    ) -> Sequence[RetrievedChunk]:
        return self.chunks[:top_k]


async def _token_stream(_messages):
    yield "A"
    yield "B"


@pytest.mark.asyncio
async def test_search_service_emits_citation_token_done() -> None:
    chunk = RetrievedChunk(
        chunk_id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        content="context",
        similarity_score=0.77,
        page_number=4,
        chunk_index=1,
        filename="a.pdf",
    )
    embeddings = MagicMock()
    embeddings.model_name = "fake"
    embeddings.embed.return_value = [[0.2] * 384]
    llm = MagicMock()
    llm.stream_chat = _token_stream

    settings = Settings(
        DATABASE_URL="postgresql+asyncpg://t:t@localhost/t",
        OPENAI_API_KEY="sk-test",
        RETRIEVAL_TOP_K=5,
        LOAD_EMBEDDING_MODEL_ON_STARTUP=False,
    )
    service = SearchService(
        settings=settings,
        embedding_provider=embeddings,
        retriever=FakeRetriever([chunk]),
        prompt_builder=PromptBuilder(),
        llm_provider=llm,
    )

    frames = [
        f
        async for f in service.stream_search(
            question="What?",
            filters=RetrievalFilters(document_id=chunk.document_id),
        )
    ]
    assert any(f.startswith("event: citation") for f in frames)
    assert any(f.startswith("event: token") for f in frames)
    done = next(f for f in frames if f.startswith("event: done"))
    data_line = done.split("data:", 1)[1].strip()
    payload = json.loads(data_line)
    assert payload["answer"] == "AB"
    assert payload["retrieved_chunk_count"] == 1
