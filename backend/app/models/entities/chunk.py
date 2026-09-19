from dataclasses import dataclass, field
from typing import Any, Optional


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
    embedding: Optional[list[float]] = None
    metadata: dict[str, Any] = field(default_factory=dict)
