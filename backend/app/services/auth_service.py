import urllib.parse
from typing import Optional, Tuple
import httpx

from app.core.config import get_settings
from app.core.exceptions import (
    AuthenticationError,
    DuplicateEntityError,
    EntityNotFoundError,
    ValidationError,
)
from app.core.logging import LoggerFactory
from app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from app.models.entities.user import UserEntity
from app.repositories.user_repository import UserRepository

logger = LoggerFactory.create_logger("AuthService")


class AuthService:
    def __init__(self, user_repo: Optional[UserRepository] = None) -> None:
        self._user_repo = user_repo or UserRepository()

    async def signup(
        self,
        name: str,
        email: str,
        password: str,
        confirm_password: Optional[str] = None,
        mobile: Optional[str] = None,
    ) -> Tuple[UserEntity, str]:
        """Register a new user, validate input, hash password, and generate auth token."""
        if not name or not name.strip():
            raise ValidationError("Name is required.")

        normalized_email = email.strip().lower()
        if not normalized_email or "@" not in normalized_email:
            raise ValidationError("A valid email address is required.")

        if not password or len(password) < 6:
            raise ValidationError("Password must be at least 6 characters long.")

        if confirm_password is not None and password != confirm_password:
            raise ValidationError("Passwords do not match.")

        existing = await self._user_repo.get_by_email(normalized_email)
        if existing:
            raise DuplicateEntityError("An account with this email already exists.")

        pwd_hash = hash_password(password)
        user = await self._user_repo.create_user(
            name=name.strip(),
            email=normalized_email,
            password_hash=pwd_hash,
            mobile=mobile.strip() if mobile else None,
            auth_provider="local",
        )

        token = create_access_token(user.id)
        logger.info("User registered successfully: %s (%s)", user.id, user.email)
        return user, token

    async def login(self, email: str, password: str) -> Tuple[UserEntity, str]:
        """Authenticate user by email and password, return user entity and token."""
        normalized_email = email.strip().lower()
        user = await self._user_repo.get_by_email(normalized_email)
        if not user or not user.password_hash:
            raise AuthenticationError("Invalid email or password.")

        if not verify_password(password, user.password_hash):
            raise AuthenticationError("Invalid email or password.")

        token = create_access_token(user.id)
        logger.info("User logged in successfully: %s", user.id)
        return user, token

    def get_google_auth_url(self, state: str = "manan_oauth_state") -> str:
        """Construct the Google OAuth 2.0 consent URL."""
        settings = get_settings()
        if not settings.google_client_id:
            logger.warning("Google OAuth attempt failed: missing GOOGLE_CLIENT_ID.")
            raise ValidationError("Google OAuth is not configured. Missing GOOGLE_CLIENT_ID.")

        logger.info(
            "Generating Google OAuth URL. Client ID present: True, Redirect URI: %s, Frontend URL: %s",
            settings.google_redirect_uri,
            getattr(settings, "frontend_url", "Not set"),
        )
        params = {
            "client_id": settings.google_client_id,
            "redirect_uri": settings.google_redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "access_type": "offline",
            "state": state,
            "prompt": "select_account",
        }
        return f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"

    async def handle_google_callback(self, code: str) -> Tuple[UserEntity, str]:
        """Exchange authorization code with Google for tokens and find/create user."""
        settings = get_settings()
        if not settings.google_client_id or not settings.google_client_secret:
            raise ValidationError("Google OAuth is not properly configured on server.")

        token_url = "https://oauth2.googleapis.com/token"
        token_payload = {
            "code": code,
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "redirect_uri": settings.google_redirect_uri,
            "grant_type": "authorization_code",
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            token_res = await client.post(token_url, data=token_payload)
            if token_res.status_code != 200:
                logger.error("Google token exchange failed: %s", token_res.text)
                raise AuthenticationError("Google authentication failed. Could not verify credentials.")

            token_data = token_res.json()
            access_token = token_data.get("access_token")

            userinfo_res = await client.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if userinfo_res.status_code != 200:
                logger.error("Google userinfo fetch failed: %s", userinfo_res.text)
                raise AuthenticationError("Could not retrieve Google profile.")

            info = userinfo_res.json()
            google_sub = info.get("sub")
            email = str(info.get("email", "")).strip().lower()
            name = info.get("name") or info.get("given_name") or email.split("@")[0]

            if not email or not google_sub:
                raise AuthenticationError("Google profile missing email or subject.")

            # 1. Check if user with this google_subject exists
            user = await self._user_repo.get_by_google_subject(google_sub)
            if not user:
                # 2. Check if user with this email exists
                user = await self._user_repo.get_by_email(email)
                if user:
                    # Link google account to existing local user safely
                    if not user.google_subject:
                        user = await self._user_repo.update_google_subject(user.id, google_sub) or user
                else:
                    # 3. Create new user with auth_provider='google'
                    user = await self._user_repo.create_user(
                        name=name,
                        email=email,
                        auth_provider="google",
                        google_subject=google_sub,
                    )

            token = create_access_token(user.id)
            logger.info("Google OAuth login successful: %s (%s)", user.id, user.email)
            return user, token

    async def change_password(
        self,
        user_id: str,
        current_password: str,
        new_password: str,
    ) -> bool:
        """Change user password after verifying current password."""
        user = await self._user_repo.get_by_id(user_id)
        if not user:
            raise EntityNotFoundError("User not found.")

        if user.auth_provider == "google" and not user.password_hash:
            raise ValidationError("This account signs in with Google. Passwords cannot be set here.")

        if not verify_password(current_password, user.password_hash):
            raise AuthenticationError("Current password is incorrect.")

        if len(new_password) < 6:
            raise ValidationError("New password must be at least 6 characters long.")

        new_hash = hash_password(new_password)
        return await self._user_repo.update_password(user_id, new_hash)

    async def update_profile(
        self,
        user_id: str,
        name: str,
        mobile: Optional[str] = None,
    ) -> UserEntity:
        """Update profile information (name, mobile)."""
        if not name or not name.strip():
            raise ValidationError("Name cannot be empty.")

        updated = await self._user_repo.update_profile(user_id, name.strip(), mobile.strip() if mobile else None)
        if not updated:
            raise EntityNotFoundError("User not found.")
        return updated
