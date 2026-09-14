from datetime import datetime, timedelta, timezone
from typing import Any
import bcrypt
import jwt

from app.core.config import get_settings
from app.core.logging import LoggerFactory

logger = LoggerFactory.create_logger("Security")


def hash_password(password: str) -> str:
    """Hash a plaintext password securely with bcrypt."""
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


get_password_hash = hash_password



def verify_password(plain_password: str, hashed_password: str | None) -> bool:
    """Verify a plaintext password against its bcrypt hash."""
    if not hashed_password or not plain_password:
        return False
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except Exception as e:
        logger.warning("Password verification error: %s", e)
        return False


def create_access_token(user_id: str, email: str | None = None, expires_delta: timedelta | None = None) -> str:
    """Create a signed JWT access token for user authentication."""
    settings = get_settings()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=settings.session_expiry_days)

    to_encode: dict[str, Any] = {
        "sub": str(user_id),
        "exp": int(expire.timestamp()),
        "iat": int(datetime.now(timezone.utc).timestamp()),
    }
    if email:
        to_encode["email"] = email

    encoded_jwt = jwt.encode(
        to_encode,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    return encoded_jwt


def decode_access_token(token: str) -> dict[str, Any] | None:
    """Decode and verify a signed JWT token. Returns full payload dict if valid, None otherwise."""
    if not token:
        return None
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        return payload
    except (jwt.PyJWTError, Exception) as e:
        logger.debug("Token decode failed: %s", e)
        return None


def verify_access_token(token: str) -> str | None:
    """Decode and verify a signed JWT token. Returns user_id if valid, None otherwise."""
    payload = decode_access_token(token)
    if payload:
        return payload.get("sub")
    return None
