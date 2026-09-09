from pydantic import BaseModel


class Document(BaseModel):
    document_id: str
    filename: str
    chunks: int


class DocumentListResponse(BaseModel):
    success: bool
    data: list[Document]