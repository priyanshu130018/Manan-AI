from pydantic import Field
from app.schemas.base import ApiResponse, BaseSchema
from app.schemas.retrieval import Citation

class ChatRequest(BaseSchema):
    session_id: str
    message: str = Field(min_length=1, max_length=10000)
    mode: str = Field(default="chat", description="Mode: 'chat' or 'study'")
    document_ids: list[str] | None = Field(
        default=None,
        description="Optional list of document IDs to scope context"
    )

class ChatData(BaseSchema):
    response: str
    citations: list[Citation] = Field(default_factory=list)
    mode: str = "chat"
    intent: str | None = None

class ChatResponse(ApiResponse[ChatData]):
    pass
