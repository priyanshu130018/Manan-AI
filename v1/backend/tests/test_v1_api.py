import pytest
from unittest.mock import AsyncMock, patch
from app.main import create_app
from app.api.dependencies import get_chat_service, get_document_service

def test_v1_health_check(client):
    res = client.get("/v1/health")
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["data"]["mode"] == "anonymous-gemini"

def test_v1_sessions_crud(client):
    # 1. List
    res_list = client.get("/v1/sessions")
    assert res_list.status_code == 200
    assert len(res_list.json()["data"]) == 1

    # 2. Get by number
    res_num = client.get("/v1/sessions/by-number/1234567890")
    assert res_num.status_code == 200
    assert res_num.json()["data"]["chat_number"] == "1234567890"

    # 3. Create
    res_create = client.post("/v1/sessions", json={"title": "Test Chat", "mode": "chat", "chat_number": "9998887776"})
    assert res_create.status_code == 200
    assert res_create.json()["data"]["title"] == "First Chat"

def test_v1_documents_crud(client):
    res_docs = client.get("/v1/documents")
    assert res_docs.status_code == 200
    assert len(res_docs.json()["data"]) == 1
    assert res_docs.json()["data"][0]["filename"] == "sample.pdf"

    res_doc = client.get("/v1/documents/doc-1")
    assert res_doc.status_code == 200

def test_v1_chat_endpoint_mocked():
    app = create_app()
    mock_chat_service = AsyncMock()
    from app.models.schemas.chat import ChatResponse
    mock_chat_service.execute.return_value = ChatResponse(
        response="Hello from anonymous Gemini V1!",
        session_id="sess-100",
        chat_number="5554443332",
        citations=[],
    )
    app.dependency_overrides[get_chat_service] = lambda: mock_chat_service

    from starlette.testclient import TestClient
    with TestClient(app) as test_client:
        res = test_client.post("/v1/chat", json={"message": "Hello Manan", "session_id": "sess-100"})
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["response"] == "Hello from anonymous Gemini V1!"
        assert data["chat_number"] == "5554443332"

def test_v1_no_auth_or_removed_endpoints(client):
    # Verify auth and study endpoints do NOT exist on /v1
    assert client.get("/v1/auth/me").status_code == 404
    assert client.post("/v1/auth/login", json={}).status_code == 404
    assert client.post("/v1/auth/signup", json={}).status_code == 404
    assert client.get("/v1/profile").status_code == 404
    assert client.get("/v1/memories").status_code == 404
    assert client.post("/v1/study/quiz/generate", json={}).status_code == 404
    assert client.post("/v1/documents").status_code == 405  # only POST /v1/documents/upload allowed
