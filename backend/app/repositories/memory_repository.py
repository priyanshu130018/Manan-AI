from datetime import datetime, timezone
import uuid
from typing import Any, Optional
from app.models.database import PostgresDatabase, get_database
from app.core.logging import LoggerFactory

logger = LoggerFactory.create_logger("MemoryRepository")


class MemoryRepository:
    def __init__(self, db: PostgresDatabase | None = None) -> None:
        self._db = db or get_database()

    def _row_to_dict(self, row: dict) -> dict[str, Any]:
        c_at = row.get("created_at")
        u_at = row.get("updated_at")
        return {
            "id": str(row["id"]),
            "user_id": str(row["user_id"]) if row.get("user_id") else None,
            "content": str(row["content"]),
            "source_session_id": str(row["source_session_id"]) if row.get("source_session_id") else None,
            "created_at": c_at.isoformat() if isinstance(c_at, datetime) else c_at,
            "updated_at": u_at.isoformat() if isinstance(u_at, datetime) else u_at,
        }

    async def create_memory(
        self,
        content: str,
        user_id: str | None = None,
        source_session_id: str | None = None,
        memory_id: str | None = None,
    ) -> dict[str, Any]:
        mid = memory_id or str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        with self._db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO memories (id, user_id, content, source_session_id, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET
                        user_id = EXCLUDED.user_id,
                        content = EXCLUDED.content,
                        updated_at = EXCLUDED.updated_at
                    RETURNING id, user_id, content, source_session_id, created_at, updated_at;
                    """,
                    (mid, user_id, content.strip(), source_session_id, now, now),
                )
                row = cur.fetchone()
                return self._row_to_dict(dict(row)) if row else {
                    "id": mid,
                    "user_id": user_id,
                    "content": content.strip(),
                    "source_session_id": source_session_id,
                    "created_at": now.isoformat(),
                    "updated_at": now.isoformat(),
                }

    async def get_memory(self, memory_id: str, user_id: str | None = None) -> Optional[dict[str, Any]]:
        with self._db.get_connection() as conn:
            with conn.cursor() as cur:
                if user_id:
                    cur.execute(
                        "SELECT id, user_id, content, source_session_id, created_at, updated_at FROM memories WHERE id = %s AND user_id = %s;",
                        (memory_id, user_id),
                    )
                else:
                    cur.execute(
                        "SELECT id, user_id, content, source_session_id, created_at, updated_at FROM memories WHERE id = %s;",
                        (memory_id,),
                    )
                row = cur.fetchone()
                return self._row_to_dict(dict(row)) if row else None

    async def update_memory(
        self,
        memory_id: str,
        content: str,
        user_id: str | None = None,
    ) -> Optional[dict[str, Any]]:
        now = datetime.now(timezone.utc)
        with self._db.get_connection() as conn:
            with conn.cursor() as cur:
                if user_id:
                    cur.execute(
                        """
                        UPDATE memories
                        SET content = %s, updated_at = %s
                        WHERE id = %s AND user_id = %s
                        RETURNING id, user_id, content, source_session_id, created_at, updated_at;
                        """,
                        (content.strip(), now, memory_id, user_id),
                    )
                else:
                    cur.execute(
                        """
                        UPDATE memories
                        SET content = %s, updated_at = %s
                        WHERE id = %s
                        RETURNING id, user_id, content, source_session_id, created_at, updated_at;
                        """,
                        (content.strip(), now, memory_id),
                    )
                row = cur.fetchone()
                return self._row_to_dict(dict(row)) if row else None

    async def list_memories(self, user_id: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        with self._db.get_connection() as conn:
            with conn.cursor() as cur:
                if user_id:
                    cur.execute(
                        """
                        SELECT id, user_id, content, source_session_id, created_at, updated_at
                        FROM memories
                        WHERE user_id = %s
                        ORDER BY created_at DESC
                        LIMIT %s;
                        """,
                        (user_id, limit),
                    )
                else:
                    cur.execute(
                        """
                        SELECT id, user_id, content, source_session_id, created_at, updated_at
                        FROM memories
                        ORDER BY created_at DESC
                        LIMIT %s;
                        """,
                        (limit,),
                    )
                rows = cur.fetchall()
                return [self._row_to_dict(dict(r)) for r in rows]

    async def delete_memory(self, memory_id: str, user_id: str | None = None) -> bool:
        with self._db.get_connection() as conn:
            with conn.cursor() as cur:
                if user_id:
                    cur.execute(
                        "DELETE FROM memories WHERE id = %s AND user_id = %s RETURNING id;",
                        (memory_id, user_id),
                    )
                else:
                    cur.execute(
                        "DELETE FROM memories WHERE id = %s RETURNING id;",
                        (memory_id,),
                    )
                return cur.fetchone() is not None

    async def clear_all_memories(self, user_id: str | None = None) -> int:
        with self._db.get_connection() as conn:
            with conn.cursor() as cur:
                if user_id:
                    cur.execute("DELETE FROM memories WHERE user_id = %s RETURNING id;", (user_id,))
                else:
                    cur.execute("DELETE FROM memories RETURNING id;")
                deleted = cur.fetchall()
                return len(deleted)
