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


def test_production_and_dev_cookie_security_attributes(monkeypatch):
    from fastapi import Response
    from app.api.routes.auth import _set_auth_cookie

    # 1. Test Production Cookie Attributes
    test_settings_prod = get_settings().model_copy(update={"env": "production"})
    with monkeypatch.context() as m:
        m.setattr("app.api.routes.auth.get_settings", lambda: test_settings_prod)
        resp_prod = Response()
        _set_auth_cookie(resp_prod, "prod-sample-token")
        raw_cookie_prod = resp_prod.headers.get("set-cookie", "").lower()
        
        assert "access_token=prod-sample-token" in raw_cookie_prod
        assert "httponly" in raw_cookie_prod
        assert "secure" in raw_cookie_prod
        assert "samesite=none" in raw_cookie_prod
        assert "path=/" in raw_cookie_prod

    # 2. Test Development Cookie Attributes
    test_settings_dev = get_settings().model_copy(update={"env": "development"})
    with monkeypatch.context() as m:
        m.setattr("app.api.routes.auth.get_settings", lambda: test_settings_dev)
        resp_dev = Response()
        _set_auth_cookie(resp_dev, "dev-sample-token")
        raw_cookie_dev = resp_dev.headers.get("set-cookie", "").lower()
        
        assert "access_token=dev-sample-token" in raw_cookie_dev
        assert "httponly" in raw_cookie_dev
        assert "samesite=lax" in raw_cookie_dev
        assert "path=/" in raw_cookie_dev
        assert "secure" not in raw_cookie_dev


def test_logout_clears_cookie_with_matching_environment_attributes(monkeypatch):
    test_settings_prod = get_settings().model_copy(update={"env": "production"})
    with monkeypatch.context() as m:
        m.setattr("app.api.routes.auth.get_settings", lambda: test_settings_prod)
        with TestClient(app) as test_client:
            res = test_client.post("/auth/logout")
            assert res.status_code == 200
            assert res.json()["data"]["authenticated"] is False
            raw_cookie = res.headers.get("set-cookie", "").lower()
            assert "access_token=" in raw_cookie
            assert "httponly" in raw_cookie
            assert "secure" in raw_cookie
            assert "samesite=none" in raw_cookie
            assert "path=/" in raw_cookie


def test_cors_configuration_origin_matching(monkeypatch):
    from app.api.middleware.cors import setup_cors
    from fastapi import FastAPI
    from starlette.middleware.cors import CORSMiddleware as StarletteCORSMiddleware

    test_settings = get_settings().model_copy(update={
        "cors_allowed_origins": "https://manan-lrvss9jw9-priyanshus-projects-6e47a451.vercel.app/, http://localhost:5173",
        "frontend_url": "https://manan-lrvss9jw9-priyanshus-projects-6e47a451.vercel.app",
    })

    with monkeypatch.context() as m:
        m.setattr("app.api.middleware.cors.get_settings", lambda: test_settings)
        test_app = FastAPI()
        setup_cors(test_app)

        # Inspect CORS middleware config
        cors_mw = next(m for m in test_app.user_middleware if m.cls == StarletteCORSMiddleware)
        assert cors_mw.kwargs["allow_credentials"] is True
        assert "https://manan-lrvss9jw9-priyanshus-projects-6e47a451.vercel.app" in cors_mw.kwargs["allow_origins"]
        assert "http://localhost:5173" in cors_mw.kwargs["allow_origins"]
        # Ensure trailing slashes are not in allowed origins
        assert "https://manan-lrvss9jw9-priyanshus-projects-6e47a451.vercel.app/" not in cors_mw.kwargs["allow_origins"]


def test_post_login_and_signup_endpoints_return_production_cookie_headers(monkeypatch):
    from unittest.mock import AsyncMock
    from app.api.routes.auth import get_auth_service

    test_user = UserEntity(
        id="user-prod-123",
        name="Production User",
        email="produser@example.com",
        auth_provider="local",
    )

    mock_auth_svc = AsyncMock()
    mock_auth_svc.login.return_value = (test_user, "prod-session-token-abc")
    mock_auth_svc.signup.return_value = (test_user, "prod-signup-token-xyz")

    test_settings_prod = get_settings().model_copy(update={"env": "production"})

    with monkeypatch.context() as m:
        m.setattr("app.api.routes.auth.get_settings", lambda: test_settings_prod)
        app.dependency_overrides[get_auth_service] = lambda: mock_auth_svc

        try:
            with TestClient(app) as test_client:
                # 1. Verify POST /auth/login response and Set-Cookie header
                res_login = test_client.post(
                    "/auth/login",
                    json={"email": "produser@example.com", "password": "Password123!"},
                )
                assert res_login.status_code == 200
                assert res_login.json()["success"] is True
                assert res_login.json()["data"]["email"] == "produser@example.com"

                raw_cookie_login = res_login.headers.get("set-cookie", "").lower()
                assert "access_token=prod-session-token-abc" in raw_cookie_login
                assert "httponly" in raw_cookie_login
                assert "secure" in raw_cookie_login
                assert "samesite=none" in raw_cookie_login
                assert "path=/" in raw_cookie_login
                assert "domain=" not in raw_cookie_login

                # 2. Verify POST /auth/signup response and Set-Cookie header
                res_signup = test_client.post(
                    "/auth/signup",
                    json={
                        "name": "Production User",
                        "email": "produser@example.com",
                        "password": "Password123!",
                    },
                )
                assert res_signup.status_code == 200
                assert res_signup.json()["success"] is True
                assert res_signup.json()["data"]["email"] == "produser@example.com"

                raw_cookie_signup = res_signup.headers.get("set-cookie", "").lower()
                assert "access_token=prod-signup-token-xyz" in raw_cookie_signup
                assert "httponly" in raw_cookie_signup
                assert "secure" in raw_cookie_signup
                assert "samesite=none" in raw_cookie_signup
                assert "path=/" in raw_cookie_signup
                assert "domain=" not in raw_cookie_signup
        finally:
            app.dependency_overrides.pop(get_auth_service, None)




