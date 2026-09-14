from dataclasses import dataclass, field
from datetime import datetime
from typing import Union, Optional
from app.models.entities.enums import AppMode


@dataclass
class SessionEntity:
    id: str
    user_id: Optional[str] = None
    title: str = "New Conversation"
    mode: AppMode = AppMode.CHAT
    selected_document_ids: list[str] = field(default_factory=list)
    chat_number: Optional[str] = None
    is_temporary: bool = False
    created_at: Union[datetime, float] = 0.0
    updated_at: Union[datetime, float] = 0.0
