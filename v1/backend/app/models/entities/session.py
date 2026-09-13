from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional
import uuid
from app.models.entities.enums import AppMode

@dataclass
class SessionEntity:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = "New Chat"
    mode: AppMode = AppMode.CHAT
    selected_document_ids: List[str] = field(default_factory=list)
    chat_number: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
