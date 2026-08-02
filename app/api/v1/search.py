"""
Semantic search / RAG query endpoints.

POST /api/v1/search streams grounded answers via Server-Sent Events (SSE).
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.core.dependencies import SearchServiceDep
from app.core.logging import get_logger
from app.rag.retrieval import RetrievalFilters
from app.schemas.common import ErrorResponse, SearchRequest
from app.services.rag_pipeline import format_sse

logger = get_logger(__name__)

router = APIRouter(tags=["Search"])


@router.post(
    "/search",
    response_class=StreamingResponse,
    responses={
        200: {
            "description": (
                "SSE stream with `citation`, `token`, and `done` events. "
                "Citations include filename, page, chunk_index, and similarity_score."
            ),
            "content": {
                "text/event-stream": {
                    "example": (
                        "event: citation\n"
                        'data: {"filename":"handbook.pdf","page_number":3,'
                        '"chunk_index":2,"similarity_score":0.81}\n\n'
                        "event: token\n"
                        'data: {"token":"Hello"}\n\n'
                        "event: done\n"
                        'data: {"answer":"Hello","citations":[],'
                        '"retrieved_chunk_count":1,"processing_time":0.42}\n\n'
                    )
                }
            },
        },
        422: {"model": ErrorResponse, "description": "Validation failure."},
        500: {"model": ErrorResponse, "description": "Unexpected processing error."},
    },
    summary="Search documents and stream a grounded answer",
)
async def search_documents(
    body: SearchRequest,
    request: Request,
    search_service: SearchServiceDep,
) -> StreamingResponse:
    """Embed the question, retrieve Top-K chunks, and stream an LLM answer."""

    filters = RetrievalFilters(
        document_id=body.document_id,
        filename=body.filename,
        tags=tuple(body.tags),
        page_number=body.page_number,
    )

    async def event_stream():
        try:
            async for frame in search_service.stream_search(
                question=body.question,
                filters=filters,
            ):
                if await request.is_disconnected():
                    logger.info("search_client_disconnected")
                    break
                yield frame
        except Exception as exc:  # noqa: BLE001
            logger.exception("search_stream_failed", error=str(exc))
            yield format_sse(
                "error",
                {"error": "processing_error", "message": "Search failed."},
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
