from dataclasses import dataclass, field
from datetime import datetime, timezone
import uuid
from app.models.entities.enums import DocumentStatus, SourceType

@dataclass
class DocumentEntity:
    document_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    original_filename: str = ""
    stored_filename: str = ""
    mime_type: str = "application/octet-stream"
    size_bytes: int = 0
    status: DocumentStatus = DocumentStatus.READY
    source_type: SourceType = SourceType.TXT
    page_count: int = 0
    chunk_count: int = 0
    processing_error: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def id(self) -> str:
        return self.document_id

    @property
    def filename(self) -> str:
        return self.original_filename

    @property
    def file_size(self) -> int:
        return self.size_bytes

    @property
    def file_type(self) -> str:
        return self.source_type.value if hasattr(self.source_type, 'value') else str(self.source_type)
