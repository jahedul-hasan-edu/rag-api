"""
Conversation chat endpoints.

POST /api/v1/chat — stream a grounded answer and persist turns (SSE)
GET  /api/v1/chat/{conversation_id} — fetch conversation history
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.core.dependencies import ChatServiceDep
from app.core.logging import get_logger
from app.rag.retrieval import RetrievalFilters
from app.schemas.common import (
    ChatRequest,
    ConversationResponse,
    ErrorResponse,
    MessageSchema,
)
from app.services.rag_pipeline import format_sse

logger = get_logger(__name__)

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post(
    "",
    response_class=StreamingResponse,
    summary="Chat with document context (SSE)",
    responses={
        200: {
            "description": (
                "SSE stream: `conversation`, `citation`, `token`, `done` events."
            ),
            "content": {"text/event-stream": {}},
        },
        404: {"model": ErrorResponse, "description": "Conversation not found."},
        422: {"model": ErrorResponse, "description": "Validation failure."},
    },
)
async def chat(
    body: ChatRequest,
    request: Request,
    chat_service: ChatServiceDep,
) -> StreamingResponse:
    """Start or continue a conversation; stream tokens and persist both turns."""

    filters = RetrievalFilters(
        document_id=body.document_id,
        filename=body.filename,
        tags=tuple(body.tags),
        page_number=body.page_number,
    )

    async def event_stream():
        try:
            async for frame in chat_service.stream_chat(
                question=body.question,
                conversation_id=body.conversation_id,
                filters=filters,
            ):
                if await request.is_disconnected():
                    logger.info("chat_client_disconnected")
                    break
                yield frame
        except Exception as exc:  # noqa: BLE001
            from app.core.exceptions import AppError

            if isinstance(exc, AppError):
                yield format_sse(
                    "error",
                    {
                        "error": exc.code,
                        "message": exc.message,
                        "details": exc.details,
                    },
                )
                return
            logger.exception("chat_stream_failed", error=str(exc))
            yield format_sse(
                "error",
                {"error": "processing_error", "message": "Chat failed."},
            )

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get(
    "/{conversation_id}",
    response_model=ConversationResponse,
    summary="Get conversation history",
    responses={
        404: {"model": ErrorResponse, "description": "Conversation not found."},
    },
)
async def get_conversation(
    conversation_id: UUID,
    chat_service: ChatServiceDep,
) -> ConversationResponse:
    """Return a conversation and its messages in chronological order."""
    conversation = await chat_service.get_conversation(conversation_id)
    messages = [
        MessageSchema(
            id=msg.id,
            role=msg.role,
            content=msg.content,
            retrieved_chunk_ids=[str(x) for x in (msg.retrieved_chunk_ids or [])],
            citations=list(msg.citations or []),
            created_at=msg.created_at,
        )
        for msg in conversation.messages
    ]
    return ConversationResponse(
        id=conversation.id,
        title=conversation.title,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        messages=messages,
    )
