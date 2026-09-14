from fastapi import APIRouter, Depends, HTTPException, status
from app.api.dependencies import get_chat_service
from app.api.dependencies.auth import get_current_user
from app.models.entities.user import UserEntity
from app.models.schemas.chat import EditMessageRequest, RegenerateRequest, ChatResponse
from app.models.schemas.base import ApiResponse
from app.services.chat_service import ChatService
from app.core.logging import LoggerFactory

logger = LoggerFactory.create_logger("MessagesRoute")

router = APIRouter(prefix="/messages", tags=["Messages"])


@router.patch("/{message_id}", response_model=ApiResponse[ChatResponse])
async def edit_message(
    message_id: str,
    request: EditMessageRequest,
    current_user: UserEntity = Depends(get_current_user),
    chat_svc: ChatService = Depends(get_chat_service),
) -> ApiResponse[ChatResponse]:
    """Edit an existing message, truncate following thread, and regenerate assistant response."""
    result = await chat_svc.edit_message_and_regenerate(
        message_id=message_id,
        new_content=request.content,
        user=current_user,
        provider=request.provider,
        model=request.model,
    )
    return ApiResponse(
        success=True,
        message="Message updated and conversation regenerated.",
        data=result,
    )


@router.post("/{message_id}/regenerate", response_model=ApiResponse[ChatResponse])
async def regenerate_message(
    message_id: str,
    request: RegenerateRequest = RegenerateRequest(),
    current_user: UserEntity = Depends(get_current_user),
    chat_svc: ChatService = Depends(get_chat_service),
) -> ApiResponse[ChatResponse]:
    """Regenerate assistant response for a given message."""
    result = await chat_svc.regenerate_response(
        message_id=message_id,
        user=current_user,
        provider=request.provider,
        model=request.model,
    )
    return ApiResponse(
        success=True,
        message="Response regenerated successfully.",
        data=result,
    )
