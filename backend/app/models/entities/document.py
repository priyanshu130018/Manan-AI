import time
from dataclasses import dataclass, field
from app.models.entities.enums import DocumentStatus, SourceType


@dataclass
class DocumentEntity:
    document_id: str
    original_filename: str
    stored_filename: str
    mime_type: str
    size_bytes: int
    user_id: str | None = None
    status: DocumentStatus = DocumentStatus.UPLOADED
    created_at: float = field(default_factory=time.time)
    page_count: int = 0
    chunk_count: int = 0
    source_type: SourceType = SourceType.PDF
    processing_error: str | None = None
