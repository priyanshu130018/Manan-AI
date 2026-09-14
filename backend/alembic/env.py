import os
import sys
from logging.config import fileConfig
from urllib.parse import urlparse

from alembic import context
from sqlalchemy import engine_from_config, pool

# Ensure both backend root and repository root are on sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
root_dir = os.path.dirname(backend_dir)

if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

try:
    from app.core.config import get_settings
    from app.core.logging import LoggerFactory
except ModuleNotFoundError:
    from app.core.config import get_settings
    from app.core.logging import LoggerFactory

logger = LoggerFactory.create_logger("Alembic")

# Alembic Config object
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set target metadata if using SQLAlchemy models (None for pure SQL/migration scripts)
target_metadata = None


def sanitize_url(raw_url: str) -> str:
    """Mask password in connection URL for safe logging."""
    try:
        parsed = urlparse(raw_url)
        if parsed.password:
            netloc = parsed.netloc
            masked_netloc = netloc.replace(f":{parsed.password}@", ":****@", 1)
            return raw_url.replace(netloc, masked_netloc, 1)
        return raw_url
    except Exception:
        return "<sanitized-db-url>"


def get_database_url() -> str:
    """Read DATABASE_URL from the application environment configuration and format for psycopg."""
    settings = get_settings()
    raw_url = os.environ.get("DATABASE_URL") or settings.database_url
    if not raw_url or not raw_url.strip():
        raise RuntimeError(
            "DATABASE_URL is not set in environment or .env file. Alembic cannot proceed."
        )

    # Sanitize and log diagnostic output
    sanitized = sanitize_url(raw_url.strip())
    logger.info("Alembic database: %s", sanitized)

    url = raw_url.strip()
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    elif url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg://", 1)
    return url


def run_migrations_offline() -> None:
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = get_database_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
