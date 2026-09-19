import pytest
from starlette.testclient import TestClient
from app.main import create_app
from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    get_password_hash,
    verify_password,
    verify_access_token,
)
from app.models.entities.user import UserEntity
from app.api.dependencies.auth import get_user_repository, get_current_user

app = create_app()

def test_password_hashing_and_jwt():
    plain = "SecurePass123!"
    hashed = get_password_hash(plain)
    assert verify_password(plain, hashed) is True
    assert verify_password("WrongPassword", hashed) is False

    token = create_access_token("user-uuid-123", "user@example.com")
    decoded_sub = verify_access_token(token)
    assert decoded_sub == "user-uuid-123"

def test_unauthenticated_requests_fail():
    with TestClient(app) as client:
        res_sessions = client.get("/sessions")
        assert res_sessions.status_code == 401

        res_docs = client.get("/doc")
        assert res_docs.status_code == 401

        res_profile = client.get("/profile")
        assert res_profile.status_code == 401

        res_memories = client.get("/memories")
        assert res_memories.status_code == 401

def test_bearer_and_cookie_authentication_flows():
    user_a = UserEntity(
        id="user-auth-test-a",
        name="User A",
        email="usera@example.com",
        auth_provider="local",
    )

    class MockUserRepo:
        async def get_by_id(self, user_id):
            if user_id == "user-auth-test-a":
                return user_a
            return None

    app.dependency_overrides[get_user_repository] = lambda: MockUserRepo()
    token = create_access_token(user_a.id, user_a.email)

    with TestClient(app) as test_client:
        # 1. Bearer Header Authentication
        res_bearer = test_client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert res_bearer.status_code == 200
        assert res_bearer.json()["data"]["email"] == "usera@example.com"

        # 2. Cookie Authentication
        test_client.cookies.set("access_token", token)
        res_cookie = test_client.get("/auth/me")
        assert res_cookie.status_code == 200
        assert res_cookie.json()["data"]["email"] == "usera@example.com"

        # 3. Invalid Bearer Token -> 401
        res_invalid = test_client.get("/auth/me", headers={"Authorization": "Bearer invalid.jwt.token"})
        assert res_invalid.status_code == 401

def test_user_session_and_memory_isolation(client):
    create_res = client.post("/sessions", json={"title": "Private User Session", "mode": "chat", "chat_number": "1122334455"})
    assert create_res.status_code == 200
    session_id = create_res.json()["data"]["id"]

    by_num = client.get("/sessions/by-number/1122334455")
    assert by_num.status_code == 200
    assert by_num.json()["data"]["title"] == "Private User Session"

    # User B
    user_b = UserEntity(id="user-b-different", name="User B", email="userb@example.com", auth_provider="local")
    client.app.dependency_overrides[get_current_user] = lambda: user_b

    b_by_num = client.get("/sessions/by-number/1122334455")
    assert b_by_num.status_code == 404

    b_by_id = client.get(f"/sessions/{session_id}")
    assert b_by_id.status_code == 404


def test_google_oauth_callback_success_redirect():
    from unittest.mock import patch, AsyncMock
    from app.api.routes.auth import get_auth_service

    google_user = UserEntity(
        id="google-user-123",
        name="Google Test User",
        email="google@example.com",
        auth_provider="google",
        google_subject="sub-12345",
    )

    mock_auth_svc = AsyncMock()
    mock_auth_svc.handle_google_callback.return_value = (google_user, "mock-google-token-xyz")

    app.dependency_overrides[get_auth_service] = lambda: mock_auth_svc

    try:
        with TestClient(app) as test_client:
            test_client.cookies.set("oauth_state", "valid-oauth-state-123")
            res = test_client.get(
                "/auth/google/callback?code=valid-code&state=valid-oauth-state-123",
                follow_redirects=False,
            )
            settings = get_settings()
            expected_url = f"{settings.frontend_url.rstrip('/')}/"
            assert res.status_code == 303
            assert res.headers.get("location") == expected_url
            assert "access_token" in res.cookies
            assert res.cookies["access_token"] == "mock-google-token-xyz"
    finally:
        app.dependency_overrides.pop(get_auth_service, None)


def test_google_oauth_callback_invalid_state_redirect():
    with TestClient(app) as test_client:
        test_client.cookies.set("oauth_state", "expected-state")
        res = test_client.get(
            "/auth/google/callback?code=valid-code&state=mismatched-state",
            follow_redirects=False,
        )
        settings = get_settings()
        expected_error_url = f"{settings.frontend_url.rstrip('/')}/login?error=invalid_state"
        assert res.status_code == 303
        assert res.headers.get("location") == expected_error_url


