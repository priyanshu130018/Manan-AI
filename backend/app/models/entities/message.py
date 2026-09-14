from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional, Union


@dataclass
class MessageEntity:
    id: str
    session_id: str
    role: str
    content: str
    citations: list[dict[str, Any]] = field(default_factory=list)
    model_used: Optional[str] = None
    provider_used: Optional[str] = None
    tokens_used: int = 0
    created_at: Union[datetime, float] = 0.0
