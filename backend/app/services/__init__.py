from app.services.chat_service import ChatService
from app.services.document_service import DocumentService
from app.services.rag_service import RAGService
from app.services.memory_service import MemoryService

# Compatibility aliases
ChatUseCase = ChatService
DocumentIngestUseCase = DocumentService
ConversationMemoryService = MemoryService

__all__ = [
    "ChatService",
    "ChatUseCase",
    "DocumentService",
    "DocumentIngestUseCase",
    "RAGService",
    "MemoryService",
    "ConversationMemoryService",
]

