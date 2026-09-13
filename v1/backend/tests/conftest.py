import os
import pytest
from starlette.testclient import TestClient
from unittest.mock import AsyncMock

from app.main import create_app
from app.models.entities.session import SessionEntity
from app.models.entities.document import DocumentEntity
from app.models.entities.enums import SourceType
from app.api.dependencies import (
    get_session_repository,
    get_document_repository,
)

@pytest.fixture
def mock_session_repo():
    repo = AsyncMock()
    repo.list_sessions.return_value = [
        SessionEntity(id="sess-1", title="First Chat", chat_number="1234567890")
    ]
    repo.get_session.return_value = SessionEntity(id="sess-1", title="First Chat", chat_number="1234567890")
    repo.get_session_by_chat_number.return_value = SessionEntity(id="sess-1", title="First Chat", chat_number="1234567890")
    repo.get_or_create_session.return_value = SessionEntity(id="sess-1", title="First Chat", chat_number="1234567890")
    repo.get_messages.return_value = []
    repo.get_summary.return_value = None
    return repo

@pytest.fixture
def mock_doc_repo():
    repo = AsyncMock()
    repo.list_all.return_value = [
        DocumentEntity(document_id="doc-1", original_filename="sample.pdf", stored_filename="sample.pdf", source_type=SourceType.PDF, size_bytes=1024, page_count=2, chunk_count=4)
    ]
    repo.get_by_id.return_value = DocumentEntity(document_id="doc-1", original_filename="sample.pdf", stored_filename="sample.pdf", source_type=SourceType.PDF, size_bytes=1024, page_count=2, chunk_count=4)
    repo.get_total_storage_bytes.return_value = 1024
    return repo

@pytest.fixture
def client(mock_session_repo, mock_doc_repo):
    app = create_app()
    app.dependency_overrides[get_session_repository] = lambda: mock_session_repo
    app.dependency_overrides[get_document_repository] = lambda: mock_doc_repo
    with TestClient(app) as test_client:
        yield test_client
