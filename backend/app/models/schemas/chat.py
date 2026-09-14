from typing import List, Optional
from pydantic import BaseModel, Field

class HistoryMessage(BaseModel):
    role: str
    content: str

class Citation(BaseModel):
    id: str
    document_id: Optional[str] = None
    filename: str
    page_number: Optional[int] = None
    page: Optional[int] = None
    chunk_index: Optional[int] = None
    source_type: Optional[str] = "pdf"
    row_range: Optional[str] = None
    table_context: Optional[str] = None
    retrieval_method: Optional[str] = None
    score: Optional[float] = None
    snippet: str = ""

CitationSchema = Citation

class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    message: str
    mode: str = "chat"
    selected_document_ids: Optional[List[str]] = None
    document_ids: Optional[List[str]] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    is_temporary: Optional[bool] = False
    history: Optional[List[HistoryMessage]] = None
    chat_number: Optional[str] = None

class ChatData(BaseModel):
    response: str
    session_id: str
    chat_number: Optional[str] = None
    chat_id: Optional[str] = None
    citations: List[Citation] = Field(default_factory=list)

ChatResponse = ChatData


class EditMessageRequest(BaseModel):
    content: str = Field(..., min_length=1)
    provider: Optional[str] = None
    model: Optional[str] = None


class RegenerateRequest(BaseModel):
    provider: Optional[str] = None
    model: Optional[str] = None
