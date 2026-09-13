from dataclasses import dataclass
from typing import Optional

@dataclass
class DocumentChunk:
    chunk_id: str
    document_id: str
    filename: str
    page_number: int
    chunk_index: int
    text: str
    source_type: str = "pdf"
    heading: Optional[str] = None
    score: float = 0.0

# Backward compatibility alias
ChunkEntity = DocumentChunk
