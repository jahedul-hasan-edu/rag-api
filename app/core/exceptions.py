"""
Application-level exceptions and FastAPI exception handlers.

All unhandled domain/HTTP errors are mapped to a consistent ErrorResponse JSON body.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import get_logger
from app.schemas.common import ErrorResponse

logger = get_logger(__name__)


class AppError(Exception):
    """Base application error with an HTTP status and machine-readable code."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "app_error",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details


class UnsupportedFileError(AppError):
    """Raised when the uploaded file type is not supported."""

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(
            message,
            code="unsupported_file",
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details,
        )


class FileTooLargeError(AppError):
    """Raised when the uploaded file exceeds the configured size limit."""

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(
            message,
            code="file_too_large",
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            details=details,
        )


class EmptyFileError(AppError):
    """Raised when the uploaded file is empty."""

    def __init__(self, message: str = "Uploaded file is empty.") -> None:
        super().__init__(
            message,
            code="empty_file",
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        )


class CorruptedFileError(AppError):
    """Raised when the uploaded file cannot be parsed."""

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(
            message,
            code="corrupted_file",
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            details=details,
        )


class ExtractionError(AppError):
    """Raised when text extraction fails unexpectedly."""

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(
            message,
            code="extraction_error",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details,
        )


class ProcessingError(AppError):
    """Raised when ingestion processing fails unexpectedly."""

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(
            message,
            code="processing_error",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details,
        )


def _error_body(
    *,
    error: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return ErrorResponse(error=error, message=message, details=details).model_dump(
        exclude_none=True
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Attach global exception handlers to the FastAPI application."""

    @app.exception_handler(AppError)
    async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
        logger.warning(
            "application_error",
            code=exc.code,
            message=exc.message,
            status_code=exc.status_code,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body(
                error=exc.code,
                message=exc.message,
                details=exc.details,
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        _request: Request,
        exc: StarletteHTTPException,
    ) -> JSONResponse:
        detail = exc.detail
        message = detail if isinstance(detail, str) else "HTTP error"
        details = detail if isinstance(detail, dict) else None
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body(
                error="http_error",
                message=message,
                details=details,
            ),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        _request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content=_error_body(
                error="validation_error",
                message="Request validation failed.",
                details={"errors": exc.errors()},
            ),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        _request: Request,
        exc: Exception,
    ) -> JSONResponse:
        logger.exception("unhandled_exception", error=str(exc))
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_error_body(
                error="internal_server_error",
                message="An unexpected error occurred.",
            ),
        )
