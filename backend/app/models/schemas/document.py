from typing import Optional
from app.models.schemas.base import ApiResponse, BaseSchema


class DocumentItem(BaseSchema):
    document_id: str
    filename: str
    chunks: int
    page_count: int = 0
    size_bytes: int = 0
    mime_type: str = "application/pdf"
    status: str = "ready"
    source_type: str = "pdf"
    created_at: float = 0.0
    processing_error: Optional[str] = None
    cloudinary_secure_url: Optional[str] = None


class DocumentListResponse(ApiResponse[list[DocumentItem]]):
    pass


class UploadData(BaseSchema):
    document_id: str
    filename: str
    chunks: int
    page_count: int = 0
    source_type: str = "pdf"
    status: str = "ready"
    cloudinary_secure_url: Optional[str] = None


class UploadResponse(ApiResponse[UploadData]):
    pass
