from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Union


@dataclass
class UserEntity:
    id: str
    name: str
    email: str
    password_hash: Optional[str] = None
    mobile: Optional[str] = None
    auth_provider: str = "local"
    google_subject: Optional[str] = None
    long_term_memory_enabled: bool = True
    preferred_model: Optional[str] = "gemini-3.6-flash"
    preferred_provider: Optional[str] = "gemini"
    created_at: Union[datetime, float] = 0.0
    updated_at: Union[datetime, float] = 0.0

    def to_profile_dict(self) -> dict:
        c_at = self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at
        u_at = self.updated_at.isoformat() if isinstance(self.updated_at, datetime) else self.updated_at
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "mobile": self.mobile,
            "auth_provider": self.auth_provider,
            "long_term_memory_enabled": self.long_term_memory_enabled,
            "preferred_model": self.preferred_model,
            "preferred_provider": self.preferred_provider,
            "created_at": c_at,
            "updated_at": u_at,
        }
