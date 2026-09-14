from enum import Enum


class AppMode(str, Enum):
    CHAT = "chat"


class DocumentStatus(str, Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class GroundingPolicy(str, Enum):
    DOCUMENTS_ONLY = "documents_only"
    DOCUMENTS_PLUS_AI = "documents_plus_ai"
    GENERAL_AI = "general_ai"


class SourceType(str, Enum):
    PDF = "pdf"
    SCANNED_PDF = "scanned_pdf"
    DOCX = "docx"
    PPTX = "pptx"
    TXT = "txt"
    IMAGE = "image"
