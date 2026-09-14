import secrets
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, EmailStr

from app.api.dependencies.auth import get_current_user
from app.core.config import get_settings
from app.core.exceptions import (
    AuthenticationError,
    DuplicateEntityError,
    ValidationError,
)
from app.core.logging import LoggerFactory
from app.models.entities.user import UserEntity
from app.models.schemas.base import ApiResponse
from app.services.auth_service import AuthService

logger = LoggerFactory.create_logger("AuthRoute")

router = APIRouter(prefix="/auth", tags=["Authentication"])
_auth_service = None


def get_auth_service() -> AuthService:
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthService()
    return _auth_service


# Request schemas
class SignupRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    confirm_password: Optional[str] = None
    mobile: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    mobile: Optional[str] = None
    auth_provider: str
    created_at: float


def _set_auth_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    max_age = settings.session_expiry_days * 24 * 3600
    is_prod = settings.env.lower() in ["prod", "production"]
    response.set_cookie(
        key="access_token",
        value=token,
        max_age=max_age,
        httponly=True,
        samesite="lax",
        secure=is_prod,
        path="/",
    )


@router.post("/signup", response_model=ApiResponse[UserResponse])
async def signup(
    body: SignupRequest,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service),
):
    """Register a new user, issue session cookie, and return user profile."""
    try:
        user, token = await auth_service.signup(
            name=body.name,
            email=body.email,
            password=body.password,
            confirm_password=body.confirm_password,
            mobile=body.mobile,
        )
        _set_auth_cookie(response, token)
        return ApiResponse(
            success=True,
            message="Account created successfully.",
            data=UserResponse(**user.to_profile_dict()),
        )
    except (ValidationError, DuplicateEntityError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/login", response_model=ApiResponse[UserResponse])
async def login(
    body: LoginRequest,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service),
):
    """Authenticate user credentials, issue session cookie, and return user profile."""
    try:
        user, token = await auth_service.login(
            email=body.email,
            password=body.password,
        )
        _set_auth_cookie(response, token)
        return ApiResponse(
            success=True,
            message="Logged in successfully.",
            data=UserResponse(**user.to_profile_dict()),
        )
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )


@router.post("/logout", response_model=ApiResponse[dict])
async def logout(response: Response):
    """Invalidate session by clearing the access_token HTTP-only cookie."""
    response.delete_cookie(
        key="access_token",
        path="/",
        httponly=True,
        samesite="lax",
    )
    return ApiResponse(
        success=True,
        message="Logged out successfully.",
        data={"authenticated": False},
    )


@router.get("/me", response_model=ApiResponse[UserResponse])
async def get_me(
    current_user: UserEntity = Depends(get_current_user),
):
    """Return the profile information of the currently authenticated user."""
    return ApiResponse(
        success=True,
        message="Current user profile.",
        data=UserResponse(**current_user.to_profile_dict()),
    )


@router.get("/google/login")
async def google_login(
    auth_service: AuthService = Depends(get_auth_service),
):
    """Initiate Google OAuth 2.0 authentication with CSRF state protection."""
    try:
        state = secrets.token_urlsafe(32)
        auth_url = auth_service.get_google_auth_url(state=state)
        response = RedirectResponse(url=auth_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)
        settings = get_settings()
        is_prod = settings.env.lower() in ["prod", "production"]
        response.set_cookie(
            key="oauth_state",
            value=state,
            max_age=600,
            httponly=True,
            samesite="lax",
            secure=is_prod,
            path="/",
        )
        return response
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/google/callback")
async def google_callback(
    request: Request,
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    auth_service: AuthService = Depends(get_auth_service),
):
    """Handle Google OAuth 2.0 authorization callback and set session cookie."""
    settings = get_settings()
    frontend_target = f"{settings.frontend_url.rstrip('/')}/"

    if error:
        logger.warning("Google OAuth denied: %s", error)
        return RedirectResponse(url=f"{settings.frontend_url.rstrip('/')}/login?error={error}")

    saved_state = request.cookies.get("oauth_state")
    if not saved_state or not state or saved_state != state:
        logger.warning("OAuth state mismatch or missing")
        return RedirectResponse(url=f"{settings.frontend_url.rstrip('/')}/login?error=invalid_state")

    if not code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing authorization code.")

    try:
        user, token = await auth_service.handle_google_callback(code)
        response = RedirectResponse(url=frontend_target, status_code=status.HTTP_307_TEMPORARY_REDIRECT)
        response.delete_cookie(key="oauth_state", path="/", httponly=True, samesite="lax")
        _set_auth_cookie(response, token)
        return response
    except Exception as e:
        logger.error("Google callback failed: %s", str(e))
        return RedirectResponse(url=f"{settings.frontend_url.rstrip('/')}/login?error=oauth_failed")

