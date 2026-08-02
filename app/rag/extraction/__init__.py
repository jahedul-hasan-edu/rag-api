"""Document extraction package."""

from app.rag.extraction.base import DocumentExtractor, ExtractedDocument, ExtractedPage
from app.rag.extraction.factory import (
    SUPPORTED_EXTENSIONS,
    get_extractor,
    resolve_mime_type,
)
from app.rag.extraction.normalize import normalize_text

__all__ = [
    "SUPPORTED_EXTENSIONS",
    "DocumentExtractor",
    "DocxExtractor",
    "ExtractedDocument",
    "ExtractedPage",
    "MarkdownExtractor",
    "PdfExtractor",
    "TextExtractor",
    "get_extractor",
    "normalize_text",
    "resolve_mime_type",
]


def __getattr__(name: str):
    """Lazy-export concrete extractors to avoid importing PyMuPDF at package import."""
    if name == "PdfExtractor":
        from app.rag.extraction.pdf import PdfExtractor

        return PdfExtractor
    if name == "DocxExtractor":
        from app.rag.extraction.docx import DocxExtractor

        return DocxExtractor
    if name == "MarkdownExtractor":
        from app.rag.extraction.text_md import MarkdownExtractor

        return MarkdownExtractor
    if name == "TextExtractor":
        from app.rag.extraction.text_plain import TextExtractor

        return TextExtractor
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
