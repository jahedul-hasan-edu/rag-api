"""Shared Pydantic schemas for API responses."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ErrorResponse(BaseModel):
    """Standardized JSON error payload."""

    model_config = ConfigDict(strict=True)

    error: str = Field(..., description="Machine-readable error code.")
    message: str = Field(..., description="Human-readable error description.")
    details: dict[str, Any] | None = Field(
        default=None,
        description="Optional structured details for debugging.",
    )


class HealthResponse(BaseModel):
    """Health check response including DB connectivity."""

    model_config = ConfigDict(strict=True)

    status: Literal["ok", "degraded"] = Field(
        ...,
        description="Overall health: ok when database is reachable.",
    )
    version: str = Field(..., description="Application version.")
    environment: str = Field(..., description="Deployment environment.")
    database: Literal["connected", "disconnected"] = Field(
        ...,
        description="Database connectivity status.",
    )


class UploadResponse(BaseModel):
    """Successful document upload / ingestion response."""

    model_config = ConfigDict(strict=True)

    document_id: UUID = Field(..., description="Persisted document identifier.")
    filename: str = Field(..., description="Original uploaded filename.")
    total_pages: int = Field(..., description="Logical page count after extraction.")
    total_chunks: int = Field(..., description="Number of chunks stored.")
    embedding_model: str = Field(..., description="Embedding model used for vectors.")
    processing_time: float = Field(
        ...,
        description="End-to-end processing time in seconds.",
    )
    status: Literal["completed", "duplicate"] = Field(
        ...,
        description=(
            "`completed` for newly ingested documents; "
            "`duplicate` when an identical SHA-256 already exists."
        ),
    )


class SearchRequest(BaseModel):
    """Semantic search / grounded Q&A request."""

    model_config = ConfigDict(strict=True)

    question: str = Field(..., min_length=1, description="User question.")
    document_id: UUID | None = Field(
        default=None,
        description="Optional document scope filter.",
    )
    filename: str | None = Field(
        default=None,
        description="Optional filename filter (SQL ILIKE pattern, e.g. %.pdf).",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Optional document metadata tags that must all match.",
    )
    page_number: int | None = Field(
        default=None,
        ge=1,
        description="Optional page-number filter.",
    )


class CitationSchema(BaseModel):
    """Citation attached to a grounded answer."""

    model_config = ConfigDict(strict=True)

    chunk_id: UUID
    document_id: UUID
    filename: str
    page_number: int | None = None
    chunk_index: int
    similarity_score: float


class ChatRequest(BaseModel):
    """Multi-turn chat request."""

    model_config = ConfigDict(strict=True)

    question: str = Field(..., min_length=1, description="User question.")
    conversation_id: UUID | None = Field(
        default=None,
        description="Existing conversation id; omit to start a new chat.",
    )
    document_id: UUID | None = None
    filename: str | None = None
    tags: list[str] = Field(default_factory=list)
    page_number: int | None = Field(default=None, ge=1)


class MessageSchema(BaseModel):
    """Persisted chat message."""

    model_config = ConfigDict(strict=True)

    id: UUID
    role: str
    content: str
    retrieved_chunk_ids: list[str] = Field(default_factory=list)
    citations: list[dict[str, Any]] = Field(default_factory=list)
    created_at: datetime


class ConversationResponse(BaseModel):
    """Conversation with ordered messages."""

    model_config = ConfigDict(strict=True)

    id: UUID
    title: str | None = None
    created_at: datetime
    updated_at: datetime
    messages: list[MessageSchema] = Field(default_factory=list)
