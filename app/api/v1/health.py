"""
Health check endpoint.

Verifies database connectivity with a lightweight SELECT 1 against the engine
(not a request-scoped session) so a down database returns degraded status
instead of a 500 from the DI layer.
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, status
from sqlalchemy import text

from app.core.dependencies import SettingsDep
from app.core.logging import get_logger
from app.db.session import get_engine
from app.schemas.common import HealthResponse

logger = get_logger(__name__)

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Application health check",
    description=(
        "Returns application version, environment, and database connectivity. "
        "Status is `ok` when the database responds; otherwise `degraded`."
    ),
    responses={
        200: {"description": "Health status payload."},
    },
)
async def health_check(settings: SettingsDep) -> HealthResponse:
    """Check process health and database connectivity."""
    database_status: Literal["connected", "disconnected"] = "disconnected"
    try:
        engine = get_engine()
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        database_status = "connected"
    except Exception as exc:
        logger.warning("database_health_check_failed", error=str(exc))
        database_status = "disconnected"

    overall: Literal["ok", "degraded"] = (
        "ok" if database_status == "connected" else "degraded"
    )

    return HealthResponse(
        status=overall,
        version=settings.app_version,
        environment=settings.environment,
        database=database_status,
    )
