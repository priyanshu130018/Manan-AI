from datetime import datetime
from typing import Any, Optional, Union
from pydantic import field_validator
from app.models.schemas.base import ApiResponse, BaseSchema


class MessageSchema(BaseSchema):
    id: str
    role: str
    content: str
    citations: Optional[list[dict[str, Any]]] = []
    created_at: float

    @field_validator("created_at", mode="before")
    @classmethod
    def parse_created_at(cls, v: Any) -> float:
        if isinstance(v, datetime):
            return v.timestamp()
        if isinstance(v, (int, float)):
            return float(v)
        try:
            return float(v)
        except Exception:
            return 0.0


class SessionSchema(BaseSchema):
    id: str
    title: str
    mode: str
    selected_document_ids: list[str] = []
    chat_number: str | None = None
    created_at: float
    updated_at: float

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def parse_timestamps(cls, v: Any) -> float:
        if isinstance(v, datetime):
            return v.timestamp()
        if isinstance(v, (int, float)):
            return float(v)
        try:
            return float(v)
        except Exception:
            return 0.0


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
