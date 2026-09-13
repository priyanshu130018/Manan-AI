from fastapi import APIRouter, Depends
from app.api.dependencies import get_chat_service
from app.services.chat_service import ChatService
from app.models.schemas.base import ApiResponse
from app.models.schemas.chat import ChatRequest, ChatResponse

router = APIRouter(prefix="/chat", tags=["Chat"])

@router.post("", response_model=ApiResponse[ChatResponse])
async def send_chat_message(
    request: ChatRequest,
    chat_service: ChatService = Depends(get_chat_service),
):
    result = await chat_service.execute(request)
    return ApiResponse(
        success=True,
        message="Response generated successfully.",
        data=result,
    )
