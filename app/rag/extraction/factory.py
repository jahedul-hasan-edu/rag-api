"""Factory that resolves a DocumentExtractor by file extension."""

from __future__ import annotations

from pathlib import Path

from app.core.exceptions import UnsupportedFileError
from app.rag.extraction.base import DocumentExtractor

SUPPORTED_EXTENSIONS: frozenset[str] = frozenset({".pdf", ".docx", ".md", ".txt"})

EXTENSION_MIME_TYPES: dict[str, str] = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".md": "text/markdown",
    ".txt": "text/plain",
}

_EXTRACTOR_CACHE: dict[str, DocumentExtractor] = {}


def get_extension(filename: str) -> str:
    """Return the lowercase file extension including the leading dot."""
    return Path(filename).suffix.lower()


def resolve_mime_type(filename: str) -> str:
    """Map a filename to a MIME type for supported extensions."""
    extension = get_extension(filename)
    mime = EXTENSION_MIME_TYPES.get(extension)
    if mime is None:
        raise UnsupportedFileError(
            f"Unsupported file type '{extension or '(none)'}'. "
            f"Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}.",
            details={"filename": filename, "extension": extension},
        )
    return mime


def _build_extractor(extension: str) -> DocumentExtractor:
    """Instantiate the extractor for *extension* (lazy imports)."""
    if extension == ".pdf":
        from app.rag.extraction.pdf import PdfExtractor

        return PdfExtractor()
    if extension == ".docx":
        from app.rag.extraction.docx import DocxExtractor

        return DocxExtractor()
    if extension == ".md":
        from app.rag.extraction.text_md import MarkdownExtractor

        return MarkdownExtractor()
    if extension == ".txt":
        from app.rag.extraction.text_plain import TextExtractor

        return TextExtractor()
    raise UnsupportedFileError(
        f"Unsupported file type '{extension or '(none)'}'. "
        f"Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}.",
        details={"extension": extension},
    )


def get_extractor(filename: str) -> DocumentExtractor:
    """Return the extractor registered for *filename*'s extension."""
    extension = get_extension(filename)
    if extension not in SUPPORTED_EXTENSIONS:
        raise UnsupportedFileError(
            f"Unsupported file type '{extension or '(none)'}'. "
            f"Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}.",
            details={"filename": filename, "extension": extension},
        )
    extractor = _EXTRACTOR_CACHE.get(extension)
    if extractor is None:
        extractor = _build_extractor(extension)
        _EXTRACTOR_CACHE[extension] = extractor
    return extractor
