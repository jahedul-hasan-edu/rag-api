"""
Shared RAG answer orchestration helpers (search + chat).
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass
from typing import Any

from app.core.logging import get_logger
from app.rag.embedding import EmbeddingProvider
from app.rag.llm import LLMProvider
from app.rag.prompts import NOT_FOUND_MESSAGE, ChatTurn, PromptBuilder
from app.rag.retrieval import RetrievedChunk, RetrievalFilters, Retriever

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class Citation:
    """Clickable citation payload for clients."""

    chunk_id: uuid.UUID
    document_id: uuid.UUID
    filename: str
    page_number: int | None
    chunk_index: int
    similarity_score: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "chunk_id": str(self.chunk_id),
            "document_id": str(self.document_id),
            "filename": self.filename,
            "page_number": self.page_number,
            "chunk_index": self.chunk_index,
            "similarity_score": round(self.similarity_score, 6),
        }


def citations_from_chunks(chunks: Sequence[RetrievedChunk]) -> list[Citation]:
    """Map retrieved chunks to citation objects."""
    return [
        Citation(
            chunk_id=chunk.chunk_id,
            document_id=chunk.document_id,
            filename=chunk.filename,
            page_number=chunk.page_number,
            chunk_index=chunk.chunk_index,
            similarity_score=chunk.similarity_score,
        )
        for chunk in chunks
    ]


def format_sse(event: str, data: dict[str, Any] | str) -> str:
    """Serialize one Server-Sent Event frame."""
    payload = data if isinstance(data, str) else json.dumps(data, ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n"


class RagAnswerPipeline:
    """
    Embed → retrieve → prompt → stream LLM.

    Shared by SearchService and ChatService so streaming / citations stay DRY.
    """

    def __init__(
        self,
        *,
        embedding_provider: EmbeddingProvider,
        retriever: Retriever,
        prompt_builder: PromptBuilder,
        llm_provider: LLMProvider,
        top_k: int = 5,
    ) -> None:
        self._embeddings = embedding_provider
        self._retriever = retriever
        self._prompts = prompt_builder
        self._llm = llm_provider
        self._top_k = top_k

    async def retrieve_chunks(
        self,
        question: str,
        *,
        filters: RetrievalFilters | None = None,
    ) -> list[RetrievedChunk]:
        embed_started = time.perf_counter()
        vectors = await asyncio.to_thread(self._embeddings.embed, [question])
        embed_ms = (time.perf_counter() - embed_started) * 1000
        logger.info(
            "query_embedding_completed",
            latency_ms=round(embed_ms, 2),
            model=self._embeddings.model_name,
        )
        if not vectors:
            return []
        chunks = await self._retriever.retrieve(
            vectors[0],
            top_k=self._top_k,
            filters=filters,
        )
        return list(chunks)

    async def stream_answer(
        self,
        *,
        question: str,
        chunks: Sequence[RetrievedChunk],
        history: Sequence[ChatTurn] | None = None,
    ) -> AsyncIterator[str]:
        """Yield assistant token fragments (or the exact not-found message)."""
        if not chunks:
            yield NOT_FOUND_MESSAGE
            return

        messages = self._prompts.build(
            question=question,
            chunks=chunks,
            history=history,
        )

        str_message = messages.__dict__ if hasattr(messages, "__dict__") else str(messages)
        logger.info(
            "prompt_built",
            message_count=len(messages),
            context_chunk_count=len(chunks),
            history_count=history and len(history) or 0,
            messages=str_message
        )
        async for token in self._llm.stream_chat(messages):
            yield token
