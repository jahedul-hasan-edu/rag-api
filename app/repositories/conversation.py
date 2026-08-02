"""SQLAlchemy Conversation / Message repositories."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Conversation, Message
from app.repositories.interfaces import ConversationRepository, MessageRepository


class SqlAlchemyConversationRepository(ConversationRepository):
    """Async SQLAlchemy-backed Conversation repository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, conversation_id: uuid.UUID) -> Conversation | None:
        result = await self._session.execute(
            select(Conversation)
            .where(Conversation.id == conversation_id)
            .options(selectinload(Conversation.messages))
        )
        return result.scalar_one_or_none()

    async def add(self, conversation: Conversation) -> Conversation:
        self._session.add(conversation)
        await self._session.flush()
        await self._session.refresh(conversation)
        return conversation

    async def touch(self, conversation: Conversation) -> Conversation:
        conversation.updated_at = datetime.now(timezone.utc)
        await self._session.flush()
        await self._session.refresh(conversation)
        return conversation


class SqlAlchemyMessageRepository(MessageRepository):
    """Async SQLAlchemy-backed Message repository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_by_conversation_id(
        self,
        conversation_id: uuid.UUID,
        *,
        limit: int | None = None,
    ) -> Sequence[Message]:
        if limit is None:
            stmt = (
                select(Message)
                .where(Message.conversation_id == conversation_id)
                .order_by(Message.created_at.asc())
            )
            result = await self._session.execute(stmt)
            return result.scalars().all()

        # Fetch the most recent *limit* messages, then return chronological order.
        stmt = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        rows = list(result.scalars().all())
        rows.reverse()
        return rows

    async def add(self, message: Message) -> Message:
        self._session.add(message)
        await self._session.flush()
        await self._session.refresh(message)
        return message

    async def add_many(self, messages: Sequence[Message]) -> Sequence[Message]:
        if not messages:
            return []
        self._session.add_all(list(messages))
        await self._session.flush()
        for message in messages:
            await self._session.refresh(message)
        return messages
