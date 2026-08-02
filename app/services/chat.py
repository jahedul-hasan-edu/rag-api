"""
Conversation-aware RAG chat service.

Persists user/assistant turns and injects recent history into prompts
up to CONVERSATION_HISTORY_LIMIT.
"""

from __future__ import annotations

import time
import uuid
from collections.abc import AsyncIterator

from app.core.config import Settings
from app.core.exceptions import ConversationNotFoundError
from app.core.logging import get_logger
from app.db.models import Conversation, Message
from app.rag.embedding import EmbeddingProvider
from app.rag.llm import LLMProvider
from app.rag.prompts import ChatTurn, PromptBuilder
from app.rag.retrieval import RetrievalFilters, Retriever
from app.repositories.interfaces import ConversationRepository, MessageRepository
from app.services.rag_pipeline import (
    RagAnswerPipeline,
    citations_from_chunks,
    format_sse,
)

logger = get_logger(__name__)


class ChatService:
    """Multi-turn RAG chat with persisted history and streaming answers."""

    def __init__(
        self,
        *,
        settings: Settings,
        conversation_repository: ConversationRepository,
        message_repository: MessageRepository,
        embedding_provider: EmbeddingProvider,
        retriever: Retriever,
        prompt_builder: PromptBuilder,
        llm_provider: LLMProvider,
    ) -> None:
        self._settings = settings
        self._conversations = conversation_repository
        self._messages = message_repository
        self._pipeline = RagAnswerPipeline(
            embedding_provider=embedding_provider,
            retriever=retriever,
            prompt_builder=prompt_builder,
            llm_provider=llm_provider,
            top_k=settings.retrieval_top_k,
        )

    async def get_conversation(self, conversation_id: uuid.UUID) -> Conversation:
        """Load a conversation with messages or raise 404."""
        conversation = await self._conversations.get_by_id(conversation_id)
        if conversation is None:
            raise ConversationNotFoundError(conversation_id)
        return conversation

    async def stream_chat(
        self,
        *,
        question: str,
        conversation_id: uuid.UUID | None = None,
        filters: RetrievalFilters | None = None,
    ) -> AsyncIterator[str]:
        """
        Stream an answer and persist both turns.

        Creates a conversation when *conversation_id* is omitted.
        """
        started = time.perf_counter()
        question = question.strip()

        if conversation_id is None:
            conversation = await self._conversations.add(
                Conversation(
                    id=uuid.uuid4(),
                    title=question[:120] or "New conversation",
                )
            )
        else:
            conversation = await self.get_conversation(conversation_id)

        history_messages = await self._messages.list_by_conversation_id(
            conversation.id,
            limit=self._settings.conversation_history_limit,
        )
        history = [
            ChatTurn(role=msg.role, content=msg.content)
            for msg in history_messages
            if msg.role in {"user", "assistant"}
        ]

        chunks = await self._pipeline.retrieve_chunks(question, filters=filters)
        citations = citations_from_chunks(chunks)
        chunk_ids = [str(c.chunk_id) for c in chunks]

        yield format_sse(
            "conversation",
            {"conversation_id": str(conversation.id)},
        )
        for citation in citations:
            yield format_sse("citation", citation.to_dict())

        answer_parts: list[str] = []
        async for token in self._pipeline.stream_answer(
            question=question,
            chunks=chunks,
            history=history,
        ):
            answer_parts.append(token)
            yield format_sse("token", {"token": token})

        answer = "".join(answer_parts)
        await self._messages.add(
            Message(
                id=uuid.uuid4(),
                conversation_id=conversation.id,
                role="user",
                content=question,
                retrieved_chunk_ids=chunk_ids,
                citations=[],
            )
        )
        await self._messages.add(
            Message(
                id=uuid.uuid4(),
                conversation_id=conversation.id,
                role="assistant",
                content=answer,
                retrieved_chunk_ids=chunk_ids,
                citations=[c.to_dict() for c in citations],
            )
        )
        await self._conversations.touch(conversation)

        elapsed = time.perf_counter() - started
        logger.info(
            "chat_completed",
            conversation_id=str(conversation.id),
            retrieved_chunk_count=len(chunks),
            total_response_time=round(elapsed, 4),
        )
        yield format_sse(
            "done",
            {
                "conversation_id": str(conversation.id),
                "answer": answer,
                "citations": [c.to_dict() for c in citations],
                "retrieved_chunk_count": len(chunks),
                "processing_time": round(elapsed, 4),
            },
        )
