from fastapi import Depends
from app.repositories.session_repository import SessionRepository
from app.repositories.document_repository import DocumentRepository
from app.services.chat_service import ChatService
from app.services.document_service import DocumentService
from app.services.rag_service import RAGService

_session_repo = None
_doc_repo = None
_rag_service = None

def get_session_repository() -> SessionRepository:
    global _session_repo
    if _session_repo is None:
        _session_repo = SessionRepository()
    return _session_repo

def get_document_repository() -> DocumentRepository:
    global _doc_repo
    if _doc_repo is None:
        _doc_repo = DocumentRepository()
    return _doc_repo

def get_rag_service() -> RAGService:
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService()
    return _rag_service

def get_document_service(
    doc_repo: DocumentRepository = Depends(get_document_repository),
) -> DocumentService:
    return DocumentService(doc_repo=doc_repo)

def get_chat_service(
    session_repo: SessionRepository = Depends(get_session_repository),
    rag_service: RAGService = Depends(get_rag_service),
) -> ChatService:
    return ChatService(session_repo=session_repo, rag_service=rag_service)
