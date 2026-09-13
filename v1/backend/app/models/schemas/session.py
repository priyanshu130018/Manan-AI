from typing import Any, Optional, List, Union
from datetime import datetime
from pydantic import BaseModel, Field

class MessageSchema(BaseModel):
    id: str
    role: str
    content: str
    citations: Optional[List[dict[str, Any]]] = None
    created_at: Union[datetime, float, int, str]

class SessionSchema(BaseModel):
    id: str
    title: str
    mode: str = "chat"
    selected_document_ids: List[str] = Field(default_factory=list)
    chat_number: Optional[str] = None
    created_at: Union[datetime, float, int, str]
    updated_at: Union[datetime, float, int, str]

class SessionDetailSchema(SessionSchema):
    messages: List[MessageSchema] = Field(default_factory=list)
    summary: Optional[str] = None

class CreateSessionRequest(BaseModel):
    id: Optional[str] = None
    title: str = "New Conversation"
    mode: str = "chat"
    selected_document_ids: List[str] = Field(default_factory=list)
    chat_number: Optional[str] = None
    messages: Optional[List[MessageSchema]] = None

class UpdateSessionRequest(BaseModel):
    title: Optional[str] = None
    mode: Optional[str] = None
    selected_document_ids: Optional[List[str]] = None
    chat_number: Optional[str] = None
