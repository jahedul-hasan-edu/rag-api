"""Shared Pydantic schemas for API responses."""

from __future__ import annotations

from typing import Any, Literal

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
