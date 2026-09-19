import time
from dataclasses import dataclass, field
from typing import Optional
from app.models.entities.enums import DocumentStatus, SourceType


@dataclass
class DocumentEntity:
    document_id: str
    original_filename: str
    stored_filename: str
    mime_type: str
    size_bytes: int
    user_id: Optional[str] = None
    status: DocumentStatus = DocumentStatus.UPLOADED
    created_at: float = field(default_factory=time.time)
    page_count: int = 0
    chunk_count: int = 0
    source_type: SourceType = SourceType.PDF
    processing_error: Optional[str] = None
    cloudinary_public_id: Optional[str] = None
    cloudinary_secure_url: Optional[str] = None
    cloudinary_resource_type: Optional[str] = None
