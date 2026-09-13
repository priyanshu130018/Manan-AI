import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class MessageEntity:
    id: str
    session_id: str
    role: str
    content: str
    citations: list[dict[str, Any]] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
