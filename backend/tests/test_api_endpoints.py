import pytest
from unittest.mock import AsyncMock, patch
from starlette.testclient import TestClient
from app.main import create_app
from app.api.dependencies import get_chat_service


def test_health_check(client):
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["status"] == "ok"


def test_list_and_create_sessions(client):
    # 1. List
    res_list = client.get("/sessions")
    assert res_list.status_code == 200
    assert res_list.json()["success"] is True

    # 2. Create
    res_create = client.post(
        "/sessions",
        json={"title": "Test Chat", "mode": "chat", "chat_number": "1234567890"},
    )
    assert res_create.status_code == 200
    assert res_create.json()["success"] is True
    assert res_create.json()["data"]["title"] == "Test Chat"


def test_get_session_by_chat_number(client):
    res = client.get("/sessions/by-number/1234567890")
    assert res.status_code in [200, 404]


def test_chat_endpoint_standardized(client):
    mock_chat_service = AsyncMock()
    from app.models.schemas.chat import ChatResponse
    mock_chat_service.execute.return_value = ChatResponse(
        response="Hello from Manan AI!",
        session_id="sess-v2-1",
        chat_number="1234567890",
        citations=[],
    )
    client.app.dependency_overrides[get_chat_service] = lambda: mock_chat_service

    res = client.post("/chat", json={"message": "Hello", "session_id": "sess-v2-1"})
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["data"]["response"] == "Hello from Manan AI!"


def test_no_duplicate_chat_or_documents_endpoints(client):
    # /chat/send was removed as a duplicate
    res_send = client.post("/chat/send", json={"message": "test"})
    assert res_send.status_code in [404, 405]

    # /documents was removed, canonical is /doc
    res_docs = client.get("/documents")
    assert res_docs.status_code == 404


def test_openapi_security_scheme_present():
    app = create_app()
    with TestClient(app) as test_client:
        res = test_client.get("/openapi.json")
        assert res.status_code == 200
        spec = res.json()
        components = spec.get("components", {})
        security_schemes = components.get("securitySchemes", {})
        assert "HTTPBearer" in security_schemes or "OAuth2PasswordBearer" in security_schemes


def test_memories_crud(client):
    from app.api.dependencies import get_memory_service
    mock_mem_svc = AsyncMock()
    mock_mem_svc.get_long_term_memories.return_value = [
        {"id": "mem-1", "user_id": "test-user-id", "content": "I like Python", "created_at": "2026-09-14T00:00:00Z", "updated_at": "2026-09-14T00:00:00Z"}
    ]
    mock_mem_svc.save_long_term_memory.return_value = {
        "id": "mem-2", "user_id": "test-user-id", "content": "Preparing for AWS certification", "created_at": "2026-09-14T00:00:00Z", "updated_at": "2026-09-14T00:00:00Z"
    }
    mock_mem_svc.update_long_term_memory.return_value = {
        "id": "mem-1", "user_id": "test-user-id", "content": "I love Python and Rust", "created_at": "2026-09-14T00:00:00Z", "updated_at": "2026-09-14T00:00:00Z"
    }
    mock_mem_svc.delete_long_term_memory.return_value = True
    client.app.dependency_overrides[get_memory_service] = lambda: mock_mem_svc

    # 1. List
    res_list = client.get("/memories")
    assert res_list.status_code == 200
    assert len(res_list.json()["data"]) == 1

    # 2. Create
    res_create = client.post("/memories", json={"content": "Preparing for AWS certification"})
    assert res_create.status_code == 200
    assert res_create.json()["data"]["content"] == "Preparing for AWS certification"

    # 3. Update
    res_update = client.patch("/memories/mem-1", json={"content": "I love Python and Rust"})
    assert res_update.status_code == 200
    assert res_update.json()["data"]["content"] == "I love Python and Rust"

    # 4. Delete
    res_del = client.delete("/memories/mem-1")
    assert res_del.status_code == 200


def test_messages_edit_and_regenerate(client):
    mock_chat_svc = AsyncMock()
    from app.models.schemas.chat import ChatResponse
    mock_chat_svc.edit_message_and_regenerate.return_value = ChatResponse(
        response="Regenerated after edit!",
        session_id="sess-1",
        chat_number="1234567890",
        citations=[],
    )
    mock_chat_svc.regenerate_response.return_value = ChatResponse(
        response="Regenerated response!",
        session_id="sess-1",
        chat_number="1234567890",
        citations=[],
    )
    client.app.dependency_overrides[get_chat_service] = lambda: mock_chat_svc

    # 1. Edit message
    res_edit = client.patch("/messages/msg-1", json={"content": "Updated question"})
    assert res_edit.status_code == 200
    assert res_edit.json()["data"]["response"] == "Regenerated after edit!"

    # 2. Regenerate message
    res_regen = client.post("/messages/msg-1/regenerate", json={})
    assert res_regen.status_code == 200
    assert res_regen.json()["data"]["response"] == "Regenerated response!"
