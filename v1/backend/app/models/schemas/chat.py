from typing import List, Optional
from pydantic import BaseModel, Field

class HistoryMessage(BaseModel):
    role: str
    content: str

class Citation(BaseModel):
    id: str
    document_id: Optional[str] = None
    filename: str
    page_number: int
    snippet: str

CitationSchema = Citation

class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    message: str
    mode: str = "chat"
    selected_document_ids: Optional[List[str]] = None
    document_ids: Optional[List[str]] = None  # alias
    is_temporary: Optional[bool] = False
    history: Optional[List[HistoryMessage]] = None
    chat_number: Optional[str] = None

class ChatData(BaseModel):
    response: str
    session_id: str
    chat_number: Optional[str] = None
    citations: List[Citation] = Field(default_factory=list)

ChatResponse = ChatData
