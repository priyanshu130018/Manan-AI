from typing import Optional
from pydantic import BaseModel, Field


class MemoryCreateRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)
    source_session_id: Optional[str] = None


class MemoryUpdateRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)


class MemoryItem(BaseModel):
    id: str
    user_id: Optional[str] = None
    content: str
    source_session_id: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
