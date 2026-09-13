import threading
from contextlib import contextmanager
from typing import Generator
from urllib.parse import urlparse

import psycopg
from psycopg.rows import dict_row

from app.core.config import get_settings
from app.core.logging import LoggerFactory

logger = LoggerFactory.create_logger("Database")


class PostgresDatabase:
    _instance = None
    _lock = threading.RLock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._init_db()
            return cls._instance

    def _ensure_database_exists(self, db_url: str) -> None:
        """Connects to the default postgres database if necessary to create target db if missing."""
        try:
            parsed = urlparse(db_url)
            dbname = parsed.path.lstrip("/")
            if not dbname:
                return

            user_part = (
                f"{parsed.username}:{parsed.password}@"
                if parsed.username and parsed.password
                else (f"{parsed.username}@" if parsed.username else "")
            )
            host_port = f"{parsed.hostname}" + (f":{parsed.port}" if parsed.port else "")
            default_url = f"{parsed.scheme}://{user_part}{host_port}/postgres"

            with psycopg.connect(default_url, autocommit=True, connect_timeout=3) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1 FROM pg_database WHERE datname = %s;", (dbname,))
                    if not cur.fetchone():
                        logger.info("Creating database '%s' in PostgreSQL...", dbname)
                        cur.execute(f'CREATE DATABASE "{dbname}";')
                        logger.info("Database '%s' created successfully.", dbname)
        except Exception as e:
            logger.debug("Database existence check skipped: %s", e)

    def _init_db(self) -> None:
        settings = get_settings()
        self._db_url = settings.database_url
        self._db_lock = threading.RLock()
        self._initialized = False

        try:
            self._ensure_database_exists(self._db_url)
            with psycopg.connect(self._db_url, row_factory=dict_row, autocommit=True) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1;")
            self._initialized = True
            logger.info("PostgreSQL database connection verified successfully.")
        except Exception as e:
            logger.warning("PostgreSQL initialization deferred (could not connect at startup: %s)", e)

    @contextmanager
    def get_connection(self) -> Generator[psycopg.Connection, None, None]:
        conn = psycopg.connect(
            self._db_url,
            row_factory=dict_row,
            autocommit=False,
        )
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()


# Aliases
SQLiteDatabase = PostgresDatabase


def get_database() -> PostgresDatabase:
    return PostgresDatabase()

