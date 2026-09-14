from typing import Any
from app.models.schemas.base import ApiResponse, BaseSchema


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
    chat_number: str | None = None
    created_at: float
    updated_at: float


class SessionDetailSchema(SessionSchema):
    messages: list[MessageSchema] = []
    summary: str | None = None


class CreateSessionRequest(BaseSchema):
    id: str | None = None
    title: str = "New Conversation"
    mode: str = "chat"
    selected_document_ids: list[str] = []
    chat_number: str | None = None
    messages: list[MessageSchema] = []


class UpdateSessionRequest(BaseSchema):
    title: str | None = None
    mode: str | None = None
    selected_document_ids: list[str] | None = None
    chat_number: str | None = None
