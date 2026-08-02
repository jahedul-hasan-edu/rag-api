"""Semantic retrieval / RagAnswerPipeline unit tests."""

from __future__ import annotations

import uuid
from typing import Sequence
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.rag.prompts import NOT_FOUND_MESSAGE, PromptBuilder
from app.rag.retrieval import RetrievedChunk, RetrievalFilters, Retriever
from app.services.rag_pipeline import RagAnswerPipeline, citations_from_chunks


class FakeRetriever(Retriever):
    def __init__(self, chunks: Sequence[RetrievedChunk]) -> None:
        self.chunks = list(chunks)
        self.last_filters: RetrievalFilters | None = None
        self.last_embedding: list[float] | None = None

    async def retrieve(
        self,
        query_embedding: list[float],
        *,
        top_k: int = 5,
        filters: RetrievalFilters | None = None,
    ) -> Sequence[RetrievedChunk]:
        self.last_embedding = query_embedding
        self.last_filters = filters
        return self.chunks[:top_k]


def _chunk() -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        content="Paris is the capital of France.",
        similarity_score=0.88,
        page_number=1,
        chunk_index=3,
        filename="geo.txt",
    )


@pytest.mark.asyncio
async def test_pipeline_retrieve_uses_embedding_and_filters() -> None:
    chunk = _chunk()
    retriever = FakeRetriever([chunk])
    embeddings = MagicMock()
    embeddings.model_name = "fake"
    embeddings.embed.return_value = [[0.1] * 384]

    llm = MagicMock()
    pipeline = RagAnswerPipeline(
        embedding_provider=embeddings,
        retriever=retriever,
        prompt_builder=PromptBuilder(),
        llm_provider=llm,
        top_k=5,
    )
    doc_id = uuid.uuid4()
    filters = RetrievalFilters(document_id=doc_id, tags=("europe",), page_number=1)
    result = await pipeline.retrieve_chunks("capital?", filters=filters)

    assert result == [chunk]
    embeddings.embed.assert_called_once_with(["capital?"])
    assert retriever.last_filters == filters
    assert retriever.last_embedding == [0.1] * 384


@pytest.mark.asyncio
async def test_pipeline_stream_answer_short_circuits_without_chunks() -> None:
    pipeline = RagAnswerPipeline(
        embedding_provider=MagicMock(),
        retriever=FakeRetriever([]),
        prompt_builder=PromptBuilder(),
        llm_provider=MagicMock(),
    )
    tokens = [t async for t in pipeline.stream_answer(question="x", chunks=[])]
    assert tokens == [NOT_FOUND_MESSAGE]


@pytest.mark.asyncio
async def test_pipeline_stream_answer_delegates_to_llm() -> None:
    async def _gen(_messages):
        for part in ("Hel", "lo"):
            yield part

    llm = MagicMock()
    llm.stream_chat = _gen
    pipeline = RagAnswerPipeline(
        embedding_provider=MagicMock(),
        retriever=FakeRetriever([]),
        prompt_builder=PromptBuilder(),
        llm_provider=llm,
    )
    tokens = [
        t
        async for t in pipeline.stream_answer(
            question="Hi?",
            chunks=[_chunk()],
        )
    ]
    assert "".join(tokens) == "Hello"


def test_citations_from_chunks() -> None:
    chunk = _chunk()
    citations = citations_from_chunks([chunk])
    assert len(citations) == 1
    payload = citations[0].to_dict()
    assert payload["filename"] == "geo.txt"
    assert payload["chunk_index"] == 3
    assert payload["page_number"] == 1
    assert "similarity_score" in payload
