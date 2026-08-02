"""Text extraction tests."""

from __future__ import annotations

import io
import zipfile

import fitz
import pytest
from docx import Document as DocxDocument

from app.core.exceptions import CorruptedFileError, UnsupportedFileError
from app.rag.extraction import get_extractor
from app.rag.extraction.docx import DocxExtractor
from app.rag.extraction.normalize import normalize_text
from app.rag.extraction.pdf import PdfExtractor
from app.rag.extraction.text_md import MarkdownExtractor
from app.rag.extraction.text_plain import TextExtractor


def _make_pdf_bytes(pages: list[str]) -> bytes:
    doc = fitz.open()
    for text in pages:
        page = doc.new_page()
        page.insert_text((72, 72), text)
    data = doc.tobytes()
    doc.close()
    return data


def _make_docx_bytes(paragraphs: list[str]) -> bytes:
    document = DocxDocument()
    for text in paragraphs:
        document.add_paragraph(text)
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def test_normalize_text_collapses_whitespace_and_line_endings() -> None:
    raw = "Hello   world\r\n\r\n\r\nNext   paragraph\r\n"
    assert normalize_text(raw) == "Hello world\n\nNext paragraph"


def test_pdf_extraction_returns_pages() -> None:
    data = _make_pdf_bytes(["Page one content.", "Page two content."])
    result = PdfExtractor().extract(data, filename="sample.pdf")
    assert result.total_pages == 2
    assert "Page one" in result.pages[0].text
    assert "Page two" in result.pages[1].text
    assert result.pages[0].page_number == 1


def test_pdf_extraction_corrupted_raises() -> None:
    with pytest.raises(CorruptedFileError):
        PdfExtractor().extract(b"not-a-pdf", filename="broken.pdf")


def test_docx_extraction() -> None:
    data = _make_docx_bytes(["First paragraph.", "Second paragraph."])
    result = DocxExtractor().extract(data, filename="notes.docx")
    assert result.total_pages == 1
    assert "First paragraph" in result.text
    assert "Second paragraph" in result.text


def test_docx_extraction_corrupted_raises() -> None:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        zf.writestr("readme.txt", "nope")
    with pytest.raises(CorruptedFileError):
        DocxExtractor().extract(buffer.getvalue(), filename="bad.docx")


def test_markdown_extraction() -> None:
    data = b"# Title\n\nHello **world**.\n"
    result = MarkdownExtractor().extract(data, filename="readme.md")
    assert result.total_pages == 1
    assert "Title" in result.text
    assert "Hello" in result.text


def test_txt_extraction() -> None:
    data = b"Line one\n\nLine two\n"
    result = TextExtractor().extract(data, filename="notes.txt")
    assert result.total_pages == 1
    assert "Line one" in result.text


def test_get_extractor_unsupported() -> None:
    with pytest.raises(UnsupportedFileError):
        get_extractor("data.csv")
