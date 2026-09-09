from typing import Any

from pydantic import BaseModel


class RetrievedChunk(BaseModel):
    id: str
    document: str
    metadata: dict[str, Any]
    distance: float


class Citation(BaseModel):
    filename: str
    chunk: int