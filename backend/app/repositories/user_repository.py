from datetime import datetime, timezone
import uuid
from typing import Optional

from app.models.database import PostgresDatabase, get_database
from app.models.entities.user import UserEntity
from app.core.logging import LoggerFactory

logger = LoggerFactory.create_logger("UserRepository")


class UserRepository:
    def __init__(self, db: PostgresDatabase | None = None) -> None:
        self._db = db or get_database()

    def _row_to_entity(self, row: dict) -> UserEntity:
        c_at = row.get("created_at")
        u_at = row.get("updated_at")
        preferred_model = row.get("preferred_model")
        preferred_provider = row.get("preferred_provider", "gemini")

        # Sanitize obsolete or legacy model values
        if preferred_model not in {"gemini-3.6-flash", "qwen3.8-27b"}:
            if preferred_model and "qwen" in str(preferred_model).lower():
                preferred_model = "qwen3.8-27b"
                preferred_provider = "qwen"
            else:
                preferred_model = "gemini-3.6-flash"
                preferred_provider = "gemini"

        return UserEntity(
            id=str(row["id"]),
            name=str(row["name"]),
            email=str(row["email"]),
            password_hash=row.get("password_hash"),
            mobile=row.get("mobile"),
            auth_provider=str(row.get("auth_provider", "local")),
            google_subject=row.get("google_subject"),
            long_term_memory_enabled=bool(row.get("long_term_memory_enabled", True)),
            preferred_model=preferred_model,
            preferred_provider=preferred_provider,
            created_at=c_at.timestamp() if isinstance(c_at, datetime) else float(c_at or 0.0),
            updated_at=u_at.timestamp() if isinstance(u_at, datetime) else float(u_at or 0.0),
        )

    async def create_user(
        self,
        name: str,
        email: str,
        password_hash: Optional[str] = None,
        mobile: Optional[str] = None,
        auth_provider: str = "local",
        google_subject: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> UserEntity:
        uid = user_id or str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        normalized_email = email.strip().lower()

        with self._db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO users (id, name, email, password_hash, mobile, auth_provider, google_subject, long_term_memory_enabled, preferred_model, preferred_provider, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, true, 'gemini-3.6-flash', 'gemini', %s, %s)
                    RETURNING id, name, email, password_hash, mobile, auth_provider, google_subject, long_term_memory_enabled, preferred_model, preferred_provider, created_at, updated_at;
                    """,
                    (uid, name.strip(), normalized_email, password_hash, mobile, auth_provider, google_subject, now, now),
                )
                row = cur.fetchone()
                return self._row_to_entity(dict(row))

    async def get_by_id(self, user_id: str) -> Optional[UserEntity]:
        with self._db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, name, email, password_hash, mobile, auth_provider, google_subject, long_term_memory_enabled, preferred_model, preferred_provider, created_at, updated_at
                    FROM users
                    WHERE id = %s;
                    """,
                    (user_id,),
                )
                row = cur.fetchone()
                return self._row_to_entity(dict(row)) if row else None

    async def get_by_email(self, email: str) -> Optional[UserEntity]:
        normalized_email = email.strip().lower()
        with self._db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, name, email, password_hash, mobile, auth_provider, google_subject, long_term_memory_enabled, preferred_model, preferred_provider, created_at, updated_at
                    FROM users
                    WHERE email = %s;
                    """,
                    (normalized_email,),
                )
                row = cur.fetchone()
                return self._row_to_entity(dict(row)) if row else None

    async def get_by_google_subject(self, google_subject: str) -> Optional[UserEntity]:
        with self._db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, name, email, password_hash, mobile, auth_provider, google_subject, long_term_memory_enabled, preferred_model, preferred_provider, created_at, updated_at
                    FROM users
                    WHERE google_subject = %s;
                    """,
                    (google_subject,),
                )
                row = cur.fetchone()
                return self._row_to_entity(dict(row)) if row else None

    async def update_profile(
        self,
        user_id: str,
        name: str,
        mobile: Optional[str] = None,
    ) -> Optional[UserEntity]:
        now = datetime.now(timezone.utc)
        with self._db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE users
                    SET name = %s, mobile = %s, updated_at = %s
                    WHERE id = %s
                    RETURNING id, name, email, password_hash, mobile, auth_provider, google_subject, long_term_memory_enabled, preferred_model, preferred_provider, created_at, updated_at;
                    """,
                    (name.strip(), mobile, now, user_id),
                )
                row = cur.fetchone()
                return self._row_to_entity(dict(row)) if row else None

    async def update_settings(
        self,
        user_id: str,
        long_term_memory_enabled: Optional[bool] = None,
        preferred_model: Optional[str] = None,
        preferred_provider: Optional[str] = None,
    ) -> Optional[UserEntity]:
        now = datetime.now(timezone.utc)
        with self._db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE users
                    SET long_term_memory_enabled = COALESCE(%s, long_term_memory_enabled),
                        preferred_model = COALESCE(%s, preferred_model),
                        preferred_provider = COALESCE(%s, preferred_provider),
                        updated_at = %s
                    WHERE id = %s
                    RETURNING id, name, email, password_hash, mobile, auth_provider, google_subject, long_term_memory_enabled, preferred_model, preferred_provider, created_at, updated_at;
                    """,
                    (long_term_memory_enabled, preferred_model, preferred_provider, now, user_id),
                )
                row = cur.fetchone()
                return self._row_to_entity(dict(row)) if row else None

    async def update_password(self, user_id: str, password_hash: str) -> bool:
        now = datetime.now(timezone.utc)
        with self._db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE users
                    SET password_hash = %s, updated_at = %s
                    WHERE id = %s
                    RETURNING id;
                    """,
                    (password_hash, now, user_id),
                )
                return cur.fetchone() is not None

    async def update_google_subject(self, user_id: str, google_subject: str) -> Optional[UserEntity]:
        now = datetime.now(timezone.utc)
        with self._db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE users
                    SET google_subject = %s, updated_at = %s
                    WHERE id = %s
                    RETURNING id, name, email, password_hash, mobile, auth_provider, google_subject, long_term_memory_enabled, preferred_model, preferred_provider, created_at, updated_at;
                    """,
                    (google_subject, now, user_id),
                )
                row = cur.fetchone()
                return self._row_to_entity(dict(row)) if row else None
