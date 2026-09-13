from typing import Any
from app.schemas.base import ApiResponse, BaseSchema

class MessageSchema(BaseSchema):
    id: str
    role: str
    content: str
    citations: list[dict[str, Any]] = []
    created_at: float

class SessionSchema(BaseSchema):
    id: str
    title: str
    mode: str
    selected_document_ids: list[str] = []
    created_at: float
    updated_at: float

class SessionDetailSchema(SessionSchema):
    messages: list[MessageSchema] = []
    summary: str = ""

class CreateSessionRequest(BaseSchema):
    title: str = "New Conversation"
    mode: str = "chat"
    selected_document_ids: list[str] = []

class UpdateSessionRequest(BaseSchema):
    title: str | None = None
    mode: str | None = None
    selected_document_ids: list[str] | None = None
