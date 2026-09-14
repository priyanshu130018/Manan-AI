from datetime import datetime, timezone
import json
import random
import uuid
from typing import Any, Optional

from app.models.database import PostgresDatabase, get_database
from app.models.entities.session import SessionEntity
from app.models.entities.message import MessageEntity
from app.models.entities.enums import AppMode
from app.utils.normalization import normalize_llm_response


def _parse_json(val: Any, default: Any = None) -> Any:
    if val is None:
        return default
    if isinstance(val, (list, dict)):
        return val
    try:
        return json.loads(val)
    except Exception:
        return default


def _generate_chat_number() -> str:
    return str(random.randint(1000000000, 9999999999))


class SessionRepository:
    def __init__(self, db: PostgresDatabase | None = None) -> None:
        self._db = db or get_database()

    def _row_to_session(self, row: dict) -> SessionEntity:
        c_at = row.get("created_at")
        u_at = row.get("updated_at")
        return SessionEntity(
            id=str(row["id"]),
            user_id=str(row["user_id"]) if row.get("user_id") else None,
            title=row.get("title", "New Conversation"),
            mode=AppMode(row["mode"]) if row.get("mode") in ["chat", "study"] else AppMode.CHAT,
            selected_document_ids=_parse_json(row.get("selected_document_ids"), []),
            chat_number=row.get("chat_number"),
            is_temporary=bool(row.get("is_temporary", False)),
            created_at=c_at.timestamp() if isinstance(c_at, datetime) else float(c_at or 0.0),
            updated_at=u_at.timestamp() if isinstance(u_at, datetime) else float(u_at or 0.0),
        )

    def _row_to_message(self, row: dict) -> MessageEntity:
        c_at = row.get("created_at")
        content_val = row.get("content", "")
        if not isinstance(content_val, str):
            content_val = normalize_llm_response(content_val)
        return MessageEntity(
            id=str(row["id"]),
            session_id=str(row["session_id"]),
            role=str(row["role"]),
            content=content_val,
            citations=_parse_json(row.get("citations"), []),
            model_used=row.get("model_used"),
            provider_used=row.get("provider_used"),
            tokens_used=int(row.get("tokens_used") or 0),
            created_at=c_at.timestamp() if isinstance(c_at, datetime) else float(c_at or 0.0),
        )

    async def get_or_create_session(
        self,
        session_id: str,
        title: str = "New Conversation",
        mode: str = "chat",
        chat_number: str | None = None,
        user_id: str | None = None,
        is_temporary: bool = False,
    ) -> SessionEntity:
        existing = await self.get_session(session_id)
        if existing:
            if user_id and not existing.user_id:
                existing.user_id = user_id
                await self.update_session(existing)
            return existing

        now = datetime.now(timezone.utc)
        chat_num = chat_number or _generate_chat_number()
        new_session = SessionEntity(
            id=session_id,
            user_id=user_id,
            title=title,
            mode=AppMode(mode) if mode in ["chat", "study"] else AppMode.CHAT,
            selected_document_ids=[],
            chat_number=chat_num,
            is_temporary=is_temporary,
            created_at=now.timestamp(),
            updated_at=now.timestamp(),
        )
        with self._db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO sessions (id, user_id, title, mode, selected_document_ids, chat_number, is_temporary, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO NOTHING;
                    """,
                    (
                        new_session.id,
                        new_session.user_id,
                        new_session.title,
                        new_session.mode.value,
                        json.dumps(new_session.selected_document_ids),
                        new_session.chat_number,
                        new_session.is_temporary,
                        now,
                        now,
                    ),
                )
        return new_session

    async def get_session(self, session_id: str, user_id: str | None = None) -> SessionEntity | None:
        with self._db.get_connection() as conn:
            with conn.cursor() as cur:
                if user_id:
                    cur.execute("SELECT * FROM sessions WHERE id = %s AND user_id = %s;", (session_id, user_id))
                else:
                    cur.execute("SELECT * FROM sessions WHERE id = %s;", (session_id,))
                row = cur.fetchone()
                return self._row_to_session(dict(row)) if row else None

    async def get_session_by_chat_number(self, chat_number: str, user_id: str | None = None) -> SessionEntity | None:
        with self._db.get_connection() as conn:
            with conn.cursor() as cur:
                if user_id:
                    cur.execute("SELECT * FROM sessions WHERE chat_number = %s AND user_id = %s;", (chat_number, user_id))
                else:
                    cur.execute("SELECT * FROM sessions WHERE chat_number = %s;", (chat_number,))
                row = cur.fetchone()
                return self._row_to_session(dict(row)) if row else None

    async def list_sessions(self, user_id: str | None = None) -> list[SessionEntity]:
        with self._db.get_connection() as conn:
            with conn.cursor() as cur:
                if user_id:
                    cur.execute(
                        "SELECT * FROM sessions WHERE user_id = %s AND is_temporary = false ORDER BY updated_at DESC;",
                        (user_id,),
                    )
                else:
                    cur.execute(
                        "SELECT * FROM sessions WHERE is_temporary = false ORDER BY updated_at DESC;"
                    )
                rows = cur.fetchall()
                return [self._row_to_session(dict(row)) for row in rows]

    async def update_session(self, session: SessionEntity) -> None:
        now = datetime.now(timezone.utc)
        session.updated_at = now.timestamp()
        with self._db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE sessions 
                    SET user_id = %s, title = %s, mode = %s, selected_document_ids = %s, chat_number = %s, is_temporary = %s, updated_at = %s
                    WHERE id = %s;
                    """,
                    (
                        session.user_id,
                        session.title,
                        session.mode.value,
                        json.dumps(session.selected_document_ids),
                        session.chat_number,
                        session.is_temporary,
                        now,
                        session.id,
                    ),
                )

    async def delete_session(self, session_id: str, user_id: str | None = None) -> None:
        with self._db.get_connection() as conn:
            with conn.cursor() as cur:
                if user_id:
                    cur.execute("SELECT id FROM sessions WHERE id = %s AND user_id = %s;", (session_id, user_id))
                    if not cur.fetchone():
                        return
                cur.execute("DELETE FROM messages WHERE session_id = %s;", (session_id,))
                cur.execute("DELETE FROM summaries WHERE session_id = %s;", (session_id,))
                cur.execute("DELETE FROM sessions WHERE id = %s;", (session_id,))

    async def add_message(self, message: MessageEntity) -> None:
        now = datetime.now(timezone.utc)
        content_str = message.content if isinstance(message.content, str) else normalize_llm_response(message.content)

        citations_val = message.citations
        if citations_val is None:
            citations_json = json.dumps([])
        elif isinstance(citations_val, str):
            try:
                json.loads(citations_val)
                citations_json = citations_val
            except Exception:
                citations_json = json.dumps([{"snippet": citations_val}])
        else:
            citations_json = json.dumps(citations_val)

        with self._db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO messages (id, session_id, role, content, citations, model_used, provider_used, tokens_used, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
                    """,
                    (
                        message.id,
                        message.session_id,
                        message.role,
                        content_str,
                        citations_json,
                        message.model_used,
                        message.provider_used,
                        message.tokens_used,
                        now,
                    ),
                )
                cur.execute("UPDATE sessions SET updated_at = %s WHERE id = %s;", (now, message.session_id))

    async def get_messages(self, session_id: str) -> list[MessageEntity]:
        with self._db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM messages WHERE session_id = %s ORDER BY created_at ASC;", (session_id,))
                rows = cur.fetchall()
                return [self._row_to_message(dict(row)) for row in rows]

    async def get_message(self, message_id: str) -> Optional[MessageEntity]:
        with self._db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM messages WHERE id = %s;", (message_id,))
                row = cur.fetchone()
                return self._row_to_message(dict(row)) if row else None

    async def update_message(self, message_id: str, new_content: str) -> Optional[MessageEntity]:
        content_str = new_content if isinstance(new_content, str) else normalize_llm_response(new_content)
        with self._db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE messages
                    SET content = %s
                    WHERE id = %s
                    RETURNING *;
                    """,
                    (content_str, message_id),
                )
                row = cur.fetchone()
                return self._row_to_message(dict(row)) if row else None

    async def delete_messages_after(self, session_id: str, created_at_ts: float) -> int:
        """Deletes messages in the session created strictly after the given timestamp (for editing/regeneration)."""
        dt = datetime.fromtimestamp(created_at_ts, timezone.utc)
        with self._db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM messages WHERE session_id = %s AND created_at > %s RETURNING id;",
                    (session_id, dt),
                )
                deleted = cur.fetchall()
                return len(deleted)

    async def get_summary(self, session_id: str) -> str:
        with self._db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT content FROM summaries WHERE session_id = %s;", (session_id,))
                row = cur.fetchone()
                return row["content"] if row else ""

    async def save_summary(self, session_id: str, summary: str, message_count: int = 0) -> None:
        now = datetime.now(timezone.utc)
        sid = str(uuid.uuid4())
        with self._db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO summaries (id, session_id, content, message_count, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (session_id) DO UPDATE SET
                        content = EXCLUDED.content,
                        message_count = EXCLUDED.message_count,
                        updated_at = EXCLUDED.updated_at;
                    """,
                    (sid, session_id, summary, message_count, now, now),
                )

    async def trim_messages(self, session_id: str, keep_last: int) -> None:
        with self._db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT created_at FROM messages WHERE session_id = %s ORDER BY created_at DESC LIMIT 1 OFFSET %s;",
                    (session_id, keep_last - 1),
                )
                row = cur.fetchone()
                if row:
                    cutoff = row["created_at"]
                    cur.execute("DELETE FROM messages WHERE session_id = %s AND created_at < %s;", (session_id, cutoff))


# Backward compatibility alias
SQLiteSessionRepository = SessionRepository
