import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock
import pytest
from fastapi.testclient import TestClient

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# Set isolated test environment variables
test_tmp_dir = tempfile.mkdtemp()
test_docs_dir = os.path.join(test_tmp_dir, "test_documents")

os.environ["APP_NAME"] = "Manan AI Test"
os.environ["ENV"] = "test"
os.environ["HOST"] = "127.0.0.1"
os.environ["PORT"] = "8000"
os.environ["DATABASE_URL"] = "postgresql://postgres:postgres@localhost:5432/manan_ai_test"
os.environ["JWT_SECRET_KEY"] = "test-secret-key-32-chars-long-minimum!!"
os.environ["JWT_ALGORITHM"] = "HS256"
os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "15"
os.environ["REFRESH_TOKEN_EXPIRE_DAYS"] = "7"
os.environ["SESSION_EXPIRY_DAYS"] = "7"
os.environ["GOOGLE_API_KEY"] = "test_google_api_key"
os.environ["GOOGLE_REDIRECT_URI"] = "http://localhost:8000/auth/google/callback"
os.environ["FRONTEND_URL"] = "http://localhost:5173"
os.environ["LLM_PROVIDER"] = "gemini"
os.environ["LLM_MODEL"] = "gemini-3.6-flash"
os.environ["QWEN_API_KEY"] = "test-qwen-api-key"
os.environ["QWEN_BASE_URL"] = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
os.environ["QWEN_MODEL"] = "qwen3.8-27b"
os.environ["CLOUDINARY_CLOUD_NAME"] = "test-cloud"
os.environ["CLOUDINARY_API_KEY"] = "test-cloudinary-key"
os.environ["CLOUDINARY_API_SECRET"] = "test-cloudinary-secret"
os.environ["CLOUDINARY_FOLDER"] = "test-manan-ai"
os.environ["EMBEDDING_PROVIDER"] = "local"
os.environ["EMBEDDING_MODEL"] = "all-MiniLM-L6-v2"
os.environ["EMBEDDING_DIMENSION"] = "384"
os.environ["UPLOAD_DIR"] = test_docs_dir
os.environ["MAX_UPLOAD_SIZE_MB"] = "50"
os.environ["TOTAL_STORAGE_LIMIT_MB"] = "500"
os.environ["CHUNK_SIZE"] = "1000"
os.environ["CHUNK_OVERLAP"] = "200"
os.environ["CORS_ALLOWED_ORIGINS"] = "http://localhost:5173,http://localhost:3000"

from app.models.database import PostgresDatabase
PostgresDatabase._init_db = lambda self: None

from app.main import create_app
from app.models.entities.user import UserEntity
from app.models.entities.session import SessionEntity
from app.models.entities.message import MessageEntity
from app.models.entities.document import DocumentEntity
from app.models.entities.chunk import DocumentChunk
from app.models.entities.enums import AppMode
from app.models.schemas.retrieval import RetrievedChunk
from app.api.dependencies import (
    get_session_repository,
    get_document_service,
    get_chat_service,
    get_memory_service,
)
from app.api.dependencies.auth import get_current_user
from app.services.memory_service import MemoryService
from app.services.chat_service import ChatService
from app.services.document_service import DocumentService

app = create_app()

@pytest.fixture(autouse=True)
def mock_db_init(monkeypatch):
    monkeypatch.setattr(PostgresDatabase, "_init_db", lambda self: None)
    monkeypatch.setattr(
        "cloudinary.uploader.upload",
        lambda file_obj, **kwargs: {
            "public_id": f"manan-ai/users/test-user-id/documents/{kwargs.get('public_id', 'doc1')}",
            "secure_url": f"https://res.cloudinary.com/test-cloud/raw/upload/test/{kwargs.get('public_id', 'doc1')}",
            "resource_type": kwargs.get("resource_type", "raw"),
        },
    )
    monkeypatch.setattr(
        "cloudinary.uploader.destroy",
        lambda public_id, **kwargs: {"result": "ok"},
    )

TEST_USER = UserEntity(
    id="test-user-id",
    name="Test User",
    email="test@example.com",
    auth_provider="local",
)


class InMemorySessionRepository:
    def __init__(self):
        self.sessions: dict[str, SessionEntity] = {}
        self.messages: dict[str, list[MessageEntity]] = {}
        self.summaries: dict[str, str] = {}

    async def get_or_create_session(
        self,
        session_id: str,
        title: str = "New Chat",
        mode: str = "chat",
        chat_number: str | None = None,
        user_id: str | None = None,
        is_temporary: bool = False,
    ) -> SessionEntity:
        if session_id not in self.sessions:
            self.sessions[session_id] = SessionEntity(
                id=session_id,
                user_id=user_id or TEST_USER.id,
                title=title,
                mode=AppMode.CHAT,
                selected_document_ids=[],
                chat_number=chat_number or "1234567890",
                is_temporary=is_temporary,
                created_at=1000.0,
                updated_at=1000.0,
            )
        return self.sessions[session_id]

    async def get_session(self, session_id: str, user_id: str | None = None) -> SessionEntity | None:
        sess = self.sessions.get(session_id)
        if sess and user_id and sess.user_id and sess.user_id != user_id:
            return None
        return sess

    async def get_session_by_chat_number(self, chat_number: str, user_id: str | None = None) -> SessionEntity | None:
        for s in self.sessions.values():
            if s.chat_number == chat_number:
                if user_id and s.user_id and s.user_id != user_id:
                    return None
                return s
        return None

    async def list_sessions(self, user_id: str | None = None) -> list[SessionEntity]:
        if user_id:
            return [s for s in self.sessions.values() if s.user_id == user_id]
        return list(self.sessions.values())

    async def update_session(self, session: SessionEntity) -> None:
        self.sessions[session.id] = session

    async def delete_session(self, session_id: str, user_id: str | None = None) -> None:
        sess = self.sessions.get(session_id)
        if sess and user_id and sess.user_id and sess.user_id != user_id:
            return
        self.sessions.pop(session_id, None)
        self.messages.pop(session_id, None)
        self.summaries.pop(session_id, None)

    async def add_message(self, message: MessageEntity) -> None:
        from app.utils.normalization import normalize_llm_response
        if not isinstance(message.content, str):
            message.content = normalize_llm_response(message.content)
        if message.session_id not in self.messages:
            self.messages[message.session_id] = []
        self.messages[message.session_id].append(message)

    async def get_messages(self, session_id: str) -> list[MessageEntity]:
        return self.messages.get(session_id, [])

    async def get_message(self, message_id: str) -> MessageEntity | None:
        for msgs in self.messages.values():
            for m in msgs:
                if m.id == message_id:
                    return m
        return None

    async def update_message(self, message_id: str, new_content: str) -> MessageEntity | None:
        from app.utils.normalization import normalize_llm_response
        m = await self.get_message(message_id)
        if m:
            m.content = new_content if isinstance(new_content, str) else normalize_llm_response(new_content)
        return m

    async def delete_messages_after(self, session_id: str, created_at_ts: float) -> int:
        if session_id not in self.messages:
            return 0
        before = len(self.messages[session_id])
        self.messages[session_id] = [m for m in self.messages[session_id] if m.created_at <= created_at_ts]
        return before - len(self.messages[session_id])

    async def delete_messages_after_message(self, session_id: str, message_id: str) -> int:
        if session_id not in self.messages:
            return 0
        msgs = self.messages[session_id]
        target_idx = None
        for idx, m in enumerate(msgs):
            if m.id == message_id:
                target_idx = idx
                break
        if target_idx is None:
            return 0
        before = len(msgs)
        self.messages[session_id] = msgs[: target_idx + 1]
        return before - len(self.messages[session_id])

    async def trim_messages(self, session_id: str, keep_last: int) -> None:
        if session_id in self.messages:
            self.messages[session_id] = self.messages[session_id][-keep_last:]

    async def save_summary(self, session_id: str, summary: str) -> None:
        self.summaries[session_id] = summary

    async def get_summary(self, session_id: str) -> str | None:
        return self.summaries.get(session_id)


class InMemoryDocumentRepository:
    def __init__(self):
        self.docs: dict[str, DocumentEntity] = {}

    async def create(self, doc: DocumentEntity) -> None:
        self.docs[doc.document_id] = doc

    async def save_document(self, doc: DocumentEntity) -> None:
        self.docs[doc.document_id] = doc

    async def get_by_id(self, document_id: str, user_id: str | None = None) -> DocumentEntity | None:
        d = self.docs.get(document_id)
        if d and user_id and d.user_id and d.user_id != user_id:
            return None
        return d

    async def get_document(self, document_id: str, user_id: str | None = None) -> DocumentEntity | None:
        return await self.get_by_id(document_id, user_id=user_id)

    async def list_all(self, user_id: str | None = None) -> list[DocumentEntity]:
        if user_id:
            return [d for d in self.docs.values() if d.user_id == user_id]
        return list(self.docs.values())

    async def list_documents(self, user_id: str | None = None) -> list[DocumentEntity]:
        return await self.list_all(user_id=user_id)

    async def update(self, doc: DocumentEntity) -> None:
        self.docs[doc.document_id] = doc

    async def delete(self, document_id: str, user_id: str | None = None) -> None:
        d = self.docs.get(document_id)
        if d and user_id and d.user_id and d.user_id != user_id:
            return
        self.docs.pop(document_id, None)

    async def delete_document(self, document_id: str, user_id: str | None = None) -> None:
        await self.delete(document_id, user_id=user_id)

    async def get_total_storage_bytes(self, user_id: str | None = None) -> int:
        if user_id:
            return sum(d.size_bytes for d in self.docs.values() if d.user_id == user_id)
        return sum(d.size_bytes for d in self.docs.values())

    async def index_chunks_fts(self, chunks, user_id: str | None = None) -> None:
        pass

    async def search_fts(self, query: str, document_ids=None, user_id=None, limit: int = 10):
        return []

    async def delete_chunks_fts(self, document_id: str, user_id: str | None = None) -> None:
        pass


class InMemoryVectorRepository:
    def __init__(self):
        self.chunks: list[dict] = []

    async def add(self, ids, documents, embeddings, metadatas, user_id=None):
        for cid, doc, emb, meta in zip(ids, documents, embeddings, metadatas):
            self.chunks.append({
                "id": cid,
                "document": doc,
                "embedding": emb,
                "metadata": meta,
                "user_id": user_id or meta.get("user_id"),
            })

    async def search(self, embedding, top_k=5, document_ids=None, user_id=None):
        res = []
        for c in self.chunks:
            if user_id and c.get("user_id") and c.get("user_id") != user_id:
                continue
            if document_ids and c["metadata"].get("document_id") not in document_ids:
                continue
            res.append(RetrievedChunk(
                id=c["id"],
                document=c["document"],
                metadata=c["metadata"],
                distance=0.1,
                score=0.9,
            ))
        return res[:top_k]

    async def delete_document(self, document_id: str, user_id: str | None = None):
        self.chunks = [
            c for c in self.chunks 
            if not (c["metadata"].get("document_id") == document_id and (not user_id or c.get("user_id") == user_id))
        ]


class InMemoryMemoryRepository:
    def __init__(self):
        self.memories: dict[str, dict] = {}

    async def create_memory(
        self,
        content: str,
        user_id: str | None = None,
        source_session_id: str | None = None,
        memory_id: str | None = None,
    ) -> dict:
        import uuid, time
        mid = memory_id or str(uuid.uuid4())
        now = time.time()
        mem = {
            "id": mid,
            "user_id": user_id or TEST_USER.id,
            "content": content,
            "source_session_id": source_session_id,
            "created_at": now,
            "updated_at": now,
        }
        self.memories[mid] = mem
        return mem

    async def list_memories(self, user_id: str | None = None, limit: int = 50) -> list[dict]:
        if user_id:
            return [m for m in self.memories.values() if m.get("user_id") == user_id][:limit]
        return list(self.memories.values())[:limit]

    async def delete_memory(self, memory_id: str, user_id: str | None = None) -> bool:
        m = self.memories.get(memory_id)
        if m and user_id and m.get("user_id") != user_id:
            return False
        return self.memories.pop(memory_id, None) is not None

    async def clear_all_memories(self, user_id: str | None = None) -> int:
        if user_id:
            to_delete = [k for k, v in self.memories.items() if v.get("user_id") == user_id]
            for k in to_delete:
                del self.memories[k]
            return len(to_delete)
        count = len(self.memories)
        self.memories.clear()
        return count


@pytest.fixture
def client(monkeypatch):
    mem_session_repo = InMemorySessionRepository()
    mem_doc_repo = InMemoryDocumentRepository()
    mem_memory_repo = InMemoryMemoryRepository()
    mem_vector_repo = InMemoryVectorRepository()

    test_mem_svc = MemoryService(session_repo=mem_session_repo, memory_repo=mem_memory_repo)
    test_chat_svc = ChatService(session_repo=mem_session_repo, memory_repo=mem_memory_repo, memory_service=test_mem_svc)
    test_doc_svc = DocumentService(doc_repo=mem_doc_repo, vector_repo=mem_vector_repo)

    app.dependency_overrides[get_current_user] = lambda: TEST_USER
    app.dependency_overrides[get_session_repository] = lambda: mem_session_repo
    app.dependency_overrides[get_memory_service] = lambda: test_mem_svc
    app.dependency_overrides[get_chat_service] = lambda: test_chat_svc
    app.dependency_overrides[get_document_service] = lambda: test_doc_svc

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def mock_llm(monkeypatch):
    mock = AsyncMock()
    mock.generate.return_value = "This is a grounded AI explanation from the documents."
    mock.generate_text.return_value = "This is a grounded AI explanation from the documents."

    monkeypatch.setattr("app.integrations.gemini.client.GeminiLLM.generate", mock.generate)
    monkeypatch.setattr("app.integrations.gemini.client.GeminiClient.generate_text", mock.generate_text)
    monkeypatch.setattr("app.integrations.qwen.client.QwenClient.generate_text", mock.generate_text)
    return mock


@pytest.fixture
def mock_embedding(monkeypatch):
    mock = AsyncMock()
    mock.embed.return_value = [0.1] * 384
    mock.embed_batch.side_effect = lambda texts, *args, **kwargs: [[0.1] * 384 for _ in texts]
    mock.embed_text.return_value = [0.1] * 384

    monkeypatch.setattr("app.integrations.gemini.client.GeminiEmbedding.embed", mock.embed)
    monkeypatch.setattr("app.integrations.gemini.client.GeminiEmbedding.embed_batch", mock.embed_batch)
    monkeypatch.setattr("app.integrations.gemini.client.GeminiClient.embed_text", mock.embed_text)
    monkeypatch.setattr("app.integrations.gemini.client.GeminiClient.embed_batch", mock.embed_batch)
    monkeypatch.setattr("app.integrations.embeddings.local.LocalEmbedding.embed", mock.embed)
    monkeypatch.setattr("app.integrations.embeddings.local.LocalEmbedding.embed_batch", mock.embed_batch)
    return mock
