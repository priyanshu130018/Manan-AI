from app.integrations.documents.base import ParsedPage
from app.integrations.documents.splitter import StructurePreservingSplitter


def test_structure_preserving_splitter_preserves_pages_and_headings():
    splitter = StructurePreservingSplitter(chunk_size=100, chunk_overlap=20)
    pages = [
        ParsedPage(page_number=1, text="First paragraph of page 1.\n\nSecond paragraph of page 1.", heading="Chapter 1"),
        ParsedPage(page_number=2, text="This is content on page 2 describing deadlocks and resource graphs.", heading="Chapter 2"),
    ]
    chunks = splitter.split_document(
        document_id="doc-123",
        filename="test.pdf",
        source_type="pdf",
        pages=pages,
    )
    assert len(chunks) >= 2
    assert chunks[0].document_id == "doc-123"
    assert chunks[0].filename == "test.pdf"
    assert chunks[0].page_number == 1
    assert chunks[0].heading == "Chapter 1"

    # Page 2 should be captured
    page2_chunks = [c for c in chunks if c.page_number == 2]
    assert len(page2_chunks) >= 1
    assert page2_chunks[0].heading == "Chapter 2"


def test_empty_pages_produce_no_chunks():
    splitter = StructurePreservingSplitter()
    chunks = splitter.split_document("doc-empty", "empty.pdf", "pdf", [])
    assert chunks == []
