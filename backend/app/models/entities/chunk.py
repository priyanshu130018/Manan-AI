from dataclasses import dataclass


@dataclass
class DocumentChunk:
    chunk_id: str
    document_id: str
    filename: str
    page_number: int
    chunk_index: int
    text: str
    source_type: str = "pdf"
    heading: str | None = None
    score: float = 0.0
