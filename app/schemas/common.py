"""Shared Pydantic schemas for API responses."""

from __future__ import annotations

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
