import time
import uuid
from app.domain.entities.message import MessageEntity
from app.domain.repositories.session_repository import SessionRepository
from app.infrastructure.persistence.sqlite.session_repo import SQLiteSessionRepository

class ConversationMemoryService:
    def __init__(self, session_repo: SessionRepository | None = None) -> None:
        self._repo = session_repo or SQLiteSessionRepository()

    async def add_user_message(self, session_id: str, content: str) -> MessageEntity:
        await self._repo.get_or_create_session(session_id)
        msg = MessageEntity(
            id=str(uuid.uuid4()),
            session_id=session_id,
            role="user",
            content=content,
            citations=[],
            created_at=time.time(),
        )
        await self._repo.add_message(msg)
        return msg

    async def add_assistant_message(self, session_id: str, content: str, citations: list[dict] | None = None) -> MessageEntity:
        await self._repo.get_or_create_session(session_id)
        msg = MessageEntity(
            id=str(uuid.uuid4()),
            session_id=session_id,
            role="assistant",
            content=content,
            citations=citations or [],
            created_at=time.time(),
        )
        await self._repo.add_message(msg)
        return msg

    async def get_history(self, session_id: str) -> list[MessageEntity]:
        return await self._repo.get_messages(session_id)

    async def get_summary(self, session_id: str) -> str:
        return await self._repo.get_summary(session_id)

    async def save_summary(self, session_id: str, summary: str) -> None:
        await self._repo.save_summary(session_id, summary)

    async def trim_history(self, session_id: str, keep_last: int = 10) -> None:
        await self._repo.trim_messages(session_id, keep_last=keep_last)
