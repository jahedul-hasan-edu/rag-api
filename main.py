"""
RAG API application entrypoint.

Creates the FastAPI app, wires middleware, exception handlers, lifespan
(DB init/dispose), and mounts the v1 API router.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1 import api_router
from app.api.v1.health import router as health_router
from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging, get_logger
from app.core.middleware import RequestContextMiddleware
from app.db.session import dispose_db, init_db

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Initialize and tear down infrastructure resources."""
    settings = get_settings()
    configure_logging(settings)
    init_db(settings)
    logger.info(
        "application_startup",
        environment=settings.environment,
        version=settings.app_version,
    )
    try:
        yield
    finally:
        await dispose_db()
        logger.info("application_shutdown")


def create_app() -> FastAPI:
    """Application factory used by uvicorn and tests."""
    settings = get_settings()

    application = FastAPI(
        title="RAG API",
        description=(
            "Production-ready Retrieval-Augmented Generation API. "
            "This phase exposes infrastructure health checks only; "
            "upload, extraction, embedding, and retrieval arrive later."
        ),
        version=settings.app_version,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    application.add_middleware(RequestContextMiddleware)
    register_exception_handlers(application)
    # Operational health at GET /health (not versioned).
    application.include_router(health_router)
    application.include_router(api_router)

    return application


app = create_app()
