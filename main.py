"""
RAG API application entrypoint.

Creates the FastAPI app, wires middleware, exception handlers, lifespan
(DB init/dispose + embedding model load), and mounts the v1 API router.
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
from app.rag.embedding import LocalBGEEmbeddingProvider

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Initialize and tear down infrastructure resources."""
    settings = get_settings()
    configure_logging(settings)
    init_db(settings)

    embedding_provider = LocalBGEEmbeddingProvider.get_instance(
        model_name=settings.embedding_model_name,
        dimension=settings.embedding_dimension,
        batch_size=settings.embedding_batch_size,
    )
    app.state.embedding_provider = embedding_provider
    if settings.load_embedding_model_on_startup:
        embedding_provider.load()

    logger.info(
        "application_startup",
        environment=settings.environment,
        version=settings.app_version,
        embedding_model=settings.embedding_model_name,
        embedding_ready=embedding_provider.is_ready(),
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
            "Production-ready Retrieval-Augmented Generation API.\n\n"
            "## Document upload\n"
            "Use `POST /api/v1/upload` with `multipart/form-data` to ingest "
            "PDF, DOCX, Markdown, or TXT files. Text is extracted, chunked "
            "(500 tokens / 100 overlap), embedded with a local BGE model, and "
            "stored in PostgreSQL via pgvector.\n\n"
            f"Default max upload size: **{settings.max_upload_size_bytes}** bytes."
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
