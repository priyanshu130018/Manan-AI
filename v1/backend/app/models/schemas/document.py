from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

class DocumentSchema(BaseModel):
    id: str
    filename: str
    file_type: str
    file_size: int
    page_count: int = 0
    chunk_count: int = 0
    created_at: datetime

class StorageStatsSchema(BaseModel):
    total_documents: int = 0
    total_storage_bytes: int = 0
    total_storage_mb: float = 0.0
    max_storage_mb: int = 500

# Aliases
DocumentItem = DocumentSchema
UploadData = DocumentSchema
