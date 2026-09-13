import json
import random
from typing import List, Optional
import psycopg
from app.core.config import get_settings
from app.models.entities.enums import AppMode
from app.models.entities.session import SessionEntity
from app.models.entities.message import MessageEntity

class SessionRepository:
    def __init__(self, db_url: Optional[str] = None):
        self.db_url = db_url or get_settings().database_url

    def _get_connection(self):
        return psycopg.connect(self.db_url, autocommit=True)

    def _generate_chat_number(self, cur) -> str:
        for _ in range(10):
            candidate = f"{random.randint(1000000000, 9999999999)}"
            cur.execute("SELECT id FROM sessions WHERE chat_number = %s", (candidate,))
            if not cur.fetchone():
                return candidate
        import time
        return str(int(time.time() * 1000))[-10:]

    async def get_or_create_session(
        self,
        session_id: str,
        title: str = "New Chat",
        mode: str = "chat",
        chat_number: Optional[str] = None,
    ) -> SessionEntity:
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, title, mode, selected_document_ids, chat_number, created_at, updated_at
                    FROM sessions WHERE id = %s
                    """,
                    (session_id,),
                )
                row = cur.fetchone()
                if row:
                    doc_ids = row[3] if isinstance(row[3], list) else (json.loads(row[3]) if row[3] else [])
                    return SessionEntity(
                        id=row[0],
                        title=row[1],
                        mode=AppMode(row[2]) if row[2] in ["chat", "study"] else AppMode.CHAT,
                        selected_document_ids=doc_ids,
                        chat_number=row[4],
                        created_at=row[5],
                        updated_at=row[6],
                    )

                assigned_chat_number = chat_number or self._generate_chat_number(cur)
                cur.execute(
                    """
                    INSERT INTO sessions (id, title, mode, selected_document_ids, chat_number)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id, title, mode, selected_document_ids, chat_number, created_at, updated_at
                    """,
                    (session_id, title, mode, json.dumps([]), assigned_chat_number),
                )
                row = cur.fetchone()
                doc_ids = row[3] if isinstance(row[3], list) else (json.loads(row[3]) if row[3] else [])
                return SessionEntity(
                    id=row[0],
                    title=row[1],
                    mode=AppMode(row[2]) if row[2] in ["chat", "study"] else AppMode.CHAT,
                    selected_document_ids=doc_ids,
                    chat_number=row[4],
                    created_at=row[5],
                    updated_at=row[6],
                )

    async def get_session(self, session_id: str) -> Optional[SessionEntity]:
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, title, mode, selected_document_ids, chat_number, created_at, updated_at
                    FROM sessions WHERE id = %s
                    """,
                    (session_id,),
                )
                row = cur.fetchone()
                if not row:
                    return None
                doc_ids = row[3] if isinstance(row[3], list) else (json.loads(row[3]) if row[3] else [])
                return SessionEntity(
                    id=row[0],
                    title=row[1],
                    mode=AppMode(row[2]) if row[2] in ["chat", "study"] else AppMode.CHAT,
                    selected_document_ids=doc_ids,
                    chat_number=row[4],
                    created_at=row[5],
                    updated_at=row[6],
                )

    async def get_session_by_chat_number(self, chat_number: str) -> Optional[SessionEntity]:
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, title, mode, selected_document_ids, chat_number, created_at, updated_at
                    FROM sessions WHERE chat_number = %s
                    """,
                    (chat_number,),
                )
                row = cur.fetchone()
                if not row:
                    return None
                doc_ids = row[3] if isinstance(row[3], list) else (json.loads(row[3]) if row[3] else [])
                return SessionEntity(
                    id=row[0],
                    title=row[1],
                    mode=AppMode(row[2]) if row[2] in ["chat", "study"] else AppMode.CHAT,
                    selected_document_ids=doc_ids,
                    chat_number=row[4],
                    created_at=row[5],
                    updated_at=row[6],
                )

    async def list_sessions(self) -> List[SessionEntity]:
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, title, mode, selected_document_ids, chat_number, created_at, updated_at
                    FROM sessions ORDER BY updated_at DESC
                    """
                )
                rows = cur.fetchall()
                sessions = []
                for row in rows:
                    doc_ids = row[3] if isinstance(row[3], list) else (json.loads(row[3]) if row[3] else [])
                    sessions.append(
                        SessionEntity(
                            id=row[0],
                            title=row[1],
                            mode=AppMode(row[2]) if row[2] in ["chat", "study"] else AppMode.CHAT,
                            selected_document_ids=doc_ids,
                            chat_number=row[4],
                            created_at=row[5],
                            updated_at=row[6],
                        )
                    )
                return sessions

    async def update_session(self, session: SessionEntity) -> None:
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE sessions
                    SET title = %s, mode = %s, selected_document_ids = %s, chat_number = %s, updated_at = NOW()
                    WHERE id = %s
                    """,
                    (
                        session.title,
                        session.mode.value,
                        json.dumps(session.selected_document_ids),
                        session.chat_number,
                        session.id,
                    ),
                )

    async def delete_session(self, session_id: str) -> None:
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM sessions WHERE id = %s", (session_id,))

    async def add_message(self, message: MessageEntity) -> None:
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO messages (id, session_id, role, content, citations, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        message.id,
                        message.session_id,
                        message.role,
                        message.content,
                        json.dumps(message.citations) if message.citations else None,
                        message.created_at,
                    ),
                )
                cur.execute("UPDATE sessions SET updated_at = NOW() WHERE id = %s", (message.session_id,))

    async def get_messages(self, session_id: str) -> List[MessageEntity]:
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, session_id, role, content, citations, created_at
                    FROM messages WHERE session_id = %s ORDER BY created_at ASC
                    """,
                    (session_id,),
                )
                rows = cur.fetchall()
                messages = []
                for row in rows:
                    citations = row[4] if isinstance(row[4], list) else (json.loads(row[4]) if row[4] else None)
                    messages.append(
                        MessageEntity(
                            id=row[0],
                            session_id=row[1],
                            role=row[2],
                            content=row[3],
                            citations=citations,
                            created_at=row[5],
                        )
                    )
                return messages

    async def get_summary(self, session_id: str) -> Optional[str]:
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT content FROM summaries WHERE session_id = %s", (session_id,))
                row = cur.fetchone()
                return row[0] if row else None

    async def set_summary(self, session_id: str, summary: str, message_count: int = 0) -> None:
        import uuid
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO summaries (id, session_id, content, message_count, updated_at)
                    VALUES (%s, %s, %s, %s, NOW())
                    ON CONFLICT (session_id) DO UPDATE
                    SET content = EXCLUDED.content, message_count = EXCLUDED.message_count, updated_at = NOW()
                    """,
                    (str(uuid.uuid4()), session_id, summary, message_count),
                )
