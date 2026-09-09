from fastapi import APIRouter

from app.schemas.chat import ChatRequest
from app.schemas.chat import ChatResponse
from app.services.chat_service import chat_service

router = APIRouter(
    prefix="/chat",
    tags=["Chat"],
)


@router.post(
    "",
    response_model=ChatResponse,
)
async def chat(
    request: ChatRequest,
) -> ChatResponse:
    return await chat_service.process(request)