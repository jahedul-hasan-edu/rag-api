"""
Document upload endpoints.

POST /api/v1/upload — multipart file ingestion pipeline.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, File, UploadFile, status

from app.core.dependencies import UploadServiceDep
from app.schemas.common import ErrorResponse, UploadResponse

router = APIRouter(tags=["Documents"])

SUPPORTED_TYPES_DOC = "PDF (`.pdf`), DOCX (`.docx`), Markdown (`.md`), TXT (`.txt`)"


@router.post(
    "/upload",
    response_model=UploadResponse,
    status_code=status.HTTP_200_OK,
    summary="Upload and ingest a document",
    description=(
        "Upload a document for text extraction, chunking, embedding, and "
        "pgvector storage.\n\n"
        f"**Supported file types:** {SUPPORTED_TYPES_DOC}\n\n"
        "**Maximum upload size:** configured via `MAX_UPLOAD_SIZE_BYTES` "
        "(default 10 MiB).\n\n"
        "Identical files (SHA-256 match) return the existing document with "
        "`status=duplicate` without reprocessing."
    ),
    responses={
        200: {
            "description": "Document ingested or duplicate detected.",
            "content": {
                "application/json": {
                    "examples": {
                        "completed": {
                            "summary": "Newly ingested document",
                            "value": {
                                "document_id": "550e8400-e29b-41d4-a716-446655440000",
                                "filename": "handbook.pdf",
                                "total_pages": 12,
                                "total_chunks": 48,
                                "embedding_model": "BAAI/bge-small-en-v1.5",
                                "processing_time": 1.8421,
                                "status": "completed",
                            },
                        },
                        "duplicate": {
                            "summary": "Duplicate content hash",
                            "value": {
                                "document_id": "550e8400-e29b-41d4-a716-446655440000",
                                "filename": "handbook.pdf",
                                "total_pages": 12,
                                "total_chunks": 48,
                                "embedding_model": "BAAI/bge-small-en-v1.5",
                                "processing_time": 0.0123,
                                "status": "duplicate",
                            },
                        },
                    }
                }
            },
        },
        400: {
            "model": ErrorResponse,
            "description": "Unsupported file type.",
            "content": {
                "application/json": {
                    "example": {
                        "error": "unsupported_file",
                        "message": "Unsupported file type '.csv'. Supported: .docx, .md, .pdf, .txt.",
                        "details": {"filename": "data.csv", "extension": ".csv"},
                    }
                }
            },
        },
        413: {
            "model": ErrorResponse,
            "description": "File too large.",
            "content": {
                "application/json": {
                    "example": {
                        "error": "file_too_large",
                        "message": "File exceeds maximum upload size of 10485760 bytes.",
                        "details": {
                            "filename": "big.pdf",
                            "size_bytes": 20971520,
                            "max_upload_size_bytes": 10485760,
                        },
                    }
                }
            },
        },
        422: {
            "model": ErrorResponse,
            "description": "Validation failure (empty or corrupted file).",
            "content": {
                "application/json": {
                    "examples": {
                        "empty": {
                            "summary": "Empty file",
                            "value": {
                                "error": "empty_file",
                                "message": "Uploaded file is empty.",
                            },
                        },
                        "corrupted": {
                            "summary": "Corrupted PDF",
                            "value": {
                                "error": "corrupted_file",
                                "message": "PDF file is corrupted or unreadable.",
                                "details": {"filename": "broken.pdf"},
                            },
                        },
                    }
                }
            },
        },
        500: {
            "model": ErrorResponse,
            "description": "Unexpected processing error.",
            "content": {
                "application/json": {
                    "example": {
                        "error": "processing_error",
                        "message": "Document processing failed.",
                    }
                }
            },
        },
    },
)
async def upload_document(
    upload_service: UploadServiceDep,
    file: Annotated[
        UploadFile,
        File(
            description=(
                f"Document to ingest. Supported: {SUPPORTED_TYPES_DOC}. "
                "Max size from MAX_UPLOAD_SIZE_BYTES (default 10 MiB)."
            ),
        ),
    ],
) -> UploadResponse:
    """Accept a multipart file upload and run the ingestion pipeline."""
    filename = file.filename or "upload.bin"
    file_bytes = await file.read()
    result = await upload_service.process(filename=filename, file_bytes=file_bytes)
    return UploadResponse(
        document_id=result.document_id,
        filename=result.filename,
        total_pages=result.total_pages,
        total_chunks=result.total_chunks,
        embedding_model=result.embedding_model,
        processing_time=result.processing_time,
        status=result.status,
    )
