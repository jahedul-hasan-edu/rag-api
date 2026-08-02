"""DOCX text extraction via python-docx."""

from __future__ import annotations

import io

from docx import Document as DocxDocument
from docx.opc.exceptions import PackageNotFoundError

from app.core.exceptions import CorruptedFileError, ExtractionError
from app.core.logging import get_logger
from app.rag.extraction.base import DocumentExtractor, ExtractedDocument, ExtractedPage
from app.rag.extraction.normalize import normalize_text

logger = get_logger(__name__)


class DocxExtractor(DocumentExtractor):
    """Extract text from DOCX bytes.

    Paragraphs are joined while preserving blank-line paragraph breaks.
    Explicit form-feed characters become logical page boundaries.
    """

    def extract(self, file_bytes: bytes, *, filename: str) -> ExtractedDocument:
        try:
            document = DocxDocument(io.BytesIO(file_bytes))
        except (PackageNotFoundError, ValueError, OSError, KeyError) as exc:
            raise CorruptedFileError(
                "DOCX file is corrupted or unreadable.",
                details={"filename": filename, "reason": str(exc)},
            ) from exc
        except Exception as exc:  # noqa: BLE001 - ZIP/XML failures map to corrupted
            raise CorruptedFileError(
                "DOCX file is corrupted or unreadable.",
                details={"filename": filename, "reason": str(exc)},
            ) from exc

        try:
            paragraph_texts = [p.text or "" for p in document.paragraphs]
            raw = "\n".join(paragraph_texts)
            parts = raw.split("\f") if "\f" in raw else [raw]
            pages = tuple(
                ExtractedPage(page_number=i + 1, text=normalize_text(part))
                for i, part in enumerate(parts)
            )
            if not pages:
                pages = (ExtractedPage(page_number=1, text=""),)

            logger.info(
                "docx_extraction_completed",
                filename=filename,
                total_pages=len(pages),
            )
            return ExtractedDocument(
                pages=pages,
                metadata={
                    "extractor": "DocxExtractor",
                    "filename": filename,
                    "page_count": len(pages),
                },
            )
        except CorruptedFileError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise ExtractionError(
                "Failed to extract text from DOCX.",
                details={"filename": filename, "reason": str(exc)},
            ) from exc
