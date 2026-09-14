from typing import Optional
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.security import verify_access_token
from app.models.entities.user import UserEntity
from app.repositories.user_repository import UserRepository

# HTTPBearer security scheme (auto_error=False to allow cookie fallback)
http_bearer = HTTPBearer(auto_error=False)

_user_repository = None


def get_user_repository() -> UserRepository:
    global _user_repository
    if _user_repository is None:
        _user_repository = UserRepository()
    return _user_repository


def _extract_token_from_request(
    request: Request,
    auth_creds: Optional[HTTPAuthorizationCredentials] = None,
) -> Optional[str]:
    # 1. Check Bearer token from HTTPBearer security dependency
    if auth_creds and auth_creds.credentials:
        return auth_creds.credentials.strip()

    # 2. Check Authorization header directly
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header[7:].strip()

    # 3. Check HTTP-only cookie
    token = request.cookies.get("access_token")
    if token:
        return token

    return None


async def get_current_user(
    request: Request,
    auth_creds: Optional[HTTPAuthorizationCredentials] = Depends(http_bearer),
    user_repo: UserRepository = Depends(get_user_repository),
) -> UserEntity:
    """Validate current user from Bearer token or HTTP-only session cookie.
    Raises 401 if unauthenticated or invalid."""
    token = _extract_token_from_request(request, auth_creds)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Please sign in to continue.",
        )

    user_id = verify_access_token(token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired or invalid. Please sign in again.",
        )

    user = await user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account not found.",
        )

    return user


async def get_optional_user(
    request: Request,
    auth_creds: Optional[HTTPAuthorizationCredentials] = Depends(http_bearer),
    user_repo: UserRepository = Depends(get_user_repository),
) -> Optional[UserEntity]:
    """Return user entity if authenticated, or None if anonymous."""
    token = _extract_token_from_request(request, auth_creds)
    if not token:
        return None

    user_id = verify_access_token(token)
    if not user_id:
        return None

    return await user_repo.get_by_id(user_id)
