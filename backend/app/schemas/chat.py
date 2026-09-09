from pydantic import Field

from app.schemas.base import ApiResponse
from app.schemas.base import BaseSchema


class ChatRequest(BaseSchema):
    session_id: str

    message: str = Field(
        min_length=1,
        max_length=5000,
    )


class Citation(BaseSchema):
    filename: str
    chunk: int


class ChatData(BaseSchema):
    response: str

    citations: list[Citation] = Field(
        default_factory=list,
    )


class ChatResponse(ApiResponse[ChatData]):
    pass