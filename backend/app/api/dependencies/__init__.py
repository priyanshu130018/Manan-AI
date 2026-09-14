from app.services.chat_service import ChatService
from app.services.document_service import DocumentService
from app.services.memory_service import MemoryService
from app.repositories.session_repository import SessionRepository

# Lazy singletons for service dependency injection
_chat_service = None
_document_service = None
_memory_service = None
_session_repository = None


def get_chat_service() -> ChatService:
    global _chat_service
    if _chat_service is None:
        _chat_service = ChatService()
    return _chat_service


def get_document_service() -> DocumentService:
    global _document_service
    if _document_service is None:
        _document_service = DocumentService()
    return _document_service


def get_memory_service() -> MemoryService:
    global _memory_service
    if _memory_service is None:
        _memory_service = MemoryService()
    return _memory_service


def get_session_repository() -> SessionRepository:
    global _session_repository
    if _session_repository is None:
        _session_repository = SessionRepository()
    return _session_repository
