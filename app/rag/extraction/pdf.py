"""PDF text extraction via PyMuPDF."""

from __future__ import annotations

from app.core.exceptions import CorruptedFileError, ExtractionError
from app.core.logging import get_logger
from app.rag.extraction.base import DocumentExtractor, ExtractedDocument, ExtractedPage
from app.rag.extraction.normalize import normalize_text

logger = get_logger(__name__)


def _import_fitz():
    try:
        import fitz
    except Exception as exc:  # noqa: BLE001 - DLL / import failures on some Windows envs
        raise ExtractionError(
            "PyMuPDF (fitz) is not available in this environment.",
            details={"reason": str(exc)},
        ) from exc
    return fitz


class PdfExtractor(DocumentExtractor):
    """Extract per-page text from PDF bytes."""

    def extract(self, file_bytes: bytes, *, filename: str) -> ExtractedDocument:
        fitz = _import_fitz()
        try:
            document = fitz.open(stream=file_bytes, filetype="pdf")
        except ExtractionError:
            raise
        except Exception as exc:  # noqa: BLE001 - surface as corrupted
            raise CorruptedFileError(
                "PDF file is corrupted or unreadable.",
                details={"filename": filename, "reason": str(exc)},
            ) from exc

        try:
            pages: list[ExtractedPage] = []
            with document:
                if document.page_count == 0:
                    raise CorruptedFileError(
                        "PDF contains no pages.",
                        details={"filename": filename},
                    )
                for index in range(document.page_count):
                    page = document.load_page(index)
                    raw = page.get_text("text") or ""
                    pages.append(
                        ExtractedPage(
                            page_number=index + 1,
                            text=normalize_text(raw),
                        )
                    )

            logger.info(
                "pdf_extraction_completed",
                filename=filename,
                total_pages=len(pages),
            )
            return ExtractedDocument(
                pages=tuple(pages),
                metadata={
                    "extractor": "PdfExtractor",
                    "filename": filename,
                    "page_count": len(pages),
                },
            )
        except (CorruptedFileError, ExtractionError):
            raise
        except Exception as exc:  # noqa: BLE001
            raise ExtractionError(
                "Failed to extract text from PDF.",
                details={"filename": filename, "reason": str(exc)},
            ) from exc
