"""
Semantic search service with SSE-oriented streaming answers + citations.
"""

from __future__ import annotations

import time
from collections.abc import AsyncIterator
from typing import Any

from app.core.config import Settings
from app.core.logging import get_logger
from app.rag.embedding import EmbeddingProvider
from app.rag.llm import LLMProvider
from app.rag.prompts import PromptBuilder
from app.rag.retrieval import RetrievalFilters, Retriever
from app.services.rag_pipeline import (
    RagAnswerPipeline,
    citations_from_chunks,
    format_sse,
)

logger = get_logger(__name__)


class SearchService:
    """One-shot RAG Q&A over uploaded documents (no conversation persistence)."""

    def __init__(
        self,
        *,
        settings: Settings,
        embedding_provider: EmbeddingProvider,
        retriever: Retriever,
        prompt_builder: PromptBuilder,
        llm_provider: LLMProvider,
    ) -> None:
        self._pipeline = RagAnswerPipeline(
            embedding_provider=embedding_provider,
            retriever=retriever,
            prompt_builder=prompt_builder,
            llm_provider=llm_provider,
            top_k=settings.retrieval_top_k,
        )

    async def stream_search(
        self,
        *,
        question: str,
        filters: RetrievalFilters | None = None,
    ) -> AsyncIterator[str]:
        """
        Yield SSE frames: optional `citation` events, `token` events, then `done`.

        Citations are emitted up front so clients can render clickable sources
        while tokens stream.
        """
        started = time.perf_counter()
        question = question.strip()
        chunks = await self._pipeline.retrieve_chunks(question, filters=filters)
        citations = citations_from_chunks(chunks)

        for citation in citations:
            yield format_sse("citation", citation.to_dict())

        answer_parts: list[str] = []
        async for token in self._pipeline.stream_answer(
            question=question,
            chunks=chunks,
        ):
            answer_parts.append(token)
            yield format_sse("token", {"token": token})

        elapsed = time.perf_counter() - started
        logger.info(
            "search_completed",
            retrieved_chunk_count=len(chunks),
            total_response_time=round(elapsed, 4),
        )
        yield format_sse(
            "done",
            {
                "answer": "".join(answer_parts),
                "citations": [c.to_dict() for c in citations],
                "retrieved_chunk_count": len(chunks),
                "processing_time": round(elapsed, 4),
            },
        )
