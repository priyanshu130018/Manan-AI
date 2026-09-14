from typing import Any
from pydantic import BaseModel


class RetrievedChunk(BaseModel):
    id: str
    document: str
    metadata: dict[str, Any]
    distance: float = 0.0
    score: float = 0.0


class Citation(BaseModel):
    document_id: str | None = None
    filename: str
    page: int | None = None
    chunk: int = 1
    text: str | None = None
    score: float | None = None
