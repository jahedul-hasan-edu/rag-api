"""ChunkingService tests."""

from __future__ import annotations

from app.rag.chunking import ChunkingService
from app.rag.extraction.base import ExtractedDocument, ExtractedPage


def _doc(text: str, *, page: int = 1) -> ExtractedDocument:
    return ExtractedDocument(pages=(ExtractedPage(page_number=page, text=text),))


def test_chunking_respects_size_and_overlap() -> None:
    service = ChunkingService(chunk_size=50, chunk_overlap=10)
    # Build text long enough to require multiple chunks
    sentence = "This is a simple sentence used for chunking tests. "
    text = sentence * 40
    chunks = service.chunk_document(_doc(text))

    assert len(chunks) > 1
    assert all(chunk.token_count <= 50 for chunk in chunks)
    assert chunks[0].chunk_index == 0
    assert chunks[0].page_number == 1
    # Indices are contiguous
    assert [c.chunk_index for c in chunks] == list(range(len(chunks)))


def test_chunking_preserves_short_paragraphs() -> None:
    service = ChunkingService(chunk_size=500, chunk_overlap=100)
    text = "Paragraph one stays whole.\n\nParagraph two also stays whole."
    chunks = service.chunk_document(_doc(text))
    assert len(chunks) == 1
    assert "Paragraph one" in chunks[0].content
    assert "Paragraph two" in chunks[0].content


def test_chunking_skips_empty_pages() -> None:
    service = ChunkingService(chunk_size=500, chunk_overlap=100)
    document = ExtractedDocument(
        pages=(
            ExtractedPage(page_number=1, text=""),
            ExtractedPage(page_number=2, text="Only this page has content."),
        )
    )
    chunks = service.chunk_document(document)
    assert len(chunks) == 1
    assert chunks[0].page_number == 2


def test_count_tokens() -> None:
    service = ChunkingService()
    assert service.count_tokens("hello world") > 0
