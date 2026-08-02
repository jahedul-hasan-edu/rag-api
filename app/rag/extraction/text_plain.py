"""Plain-text extraction."""

from __future__ import annotations

from app.core.exceptions import CorruptedFileError, ExtractionError
from app.core.logging import get_logger
from app.rag.extraction.base import DocumentExtractor, ExtractedDocument, ExtractedPage
from app.rag.extraction.normalize import normalize_text

logger = get_logger(__name__)


class TextExtractor(DocumentExtractor):
    """Extract UTF-8 plain text as a single logical page (split on form feeds)."""

    def extract(self, file_bytes: bytes, *, filename: str) -> ExtractedDocument:
        try:
            try:
                raw = file_bytes.decode("utf-8")
            except UnicodeDecodeError:
                raw = file_bytes.decode("utf-8", errors="replace")

            parts = raw.split("\f") if "\f" in raw else [raw]
            pages = tuple(
                ExtractedPage(page_number=i + 1, text=normalize_text(part))
                for i, part in enumerate(parts)
            )
            if not pages:
                raise CorruptedFileError(
                    "Text file could not be read.",
                    details={"filename": filename},
                )

            logger.info(
                "text_extraction_completed",
                filename=filename,
                total_pages=len(pages),
            )
            return ExtractedDocument(
                pages=pages,
                metadata={
                    "extractor": "TextExtractor",
                    "filename": filename,
                    "page_count": len(pages),
                },
            )
        except CorruptedFileError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise ExtractionError(
                "Failed to extract text from TXT.",
                details={"filename": filename, "reason": str(exc)},
            ) from exc
