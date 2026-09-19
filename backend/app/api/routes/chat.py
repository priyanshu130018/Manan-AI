from typing import Optional
from fastapi import APIRouter, Depends, Header, HTTPException
from app.api.dependencies import get_chat_service, get_session_repository
from app.api.dependencies.auth import get_current_user
from app.models.entities.user import UserEntity
from app.repositories.session_repository import SessionRepository
from app.services.chat_service import ChatService
from app.models.schemas.chat import ChatRequest, ChatResponse
from app.models.schemas.base import ApiResponse
from app.models.schemas.session import SessionDetailSchema, MessageSchema

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("", response_model=ApiResponse[ChatResponse])
async def chat_endpoint(
    request: ChatRequest,
    x_model_name: Optional[str] = Header(None, alias="X-Model-Name"),
    current_user: UserEntity = Depends(get_current_user),
    chat_svc: ChatService = Depends(get_chat_service),
) -> ApiResponse[ChatResponse]:
    """Process a chat message, perform RAG retrieval, and return assistant response with citations."""
    if not request.model and x_model_name:
        request.model = x_model_name
    result = await chat_svc.execute(request, user=current_user)
    return ApiResponse(
        success=True,
        message="Response generated successfully.",
        data=result,
    )


@router.get("/{chat_number}", response_model=ApiResponse[SessionDetailSchema])
async def get_shared_chat(
    chat_number: str,
    session_repo: SessionRepository = Depends(get_session_repository),
):
    """Public read-only access to a conversation via its 10-digit chat number."""
    if not chat_number.isdigit() or len(chat_number) != 10:
        raise HTTPException(status_code=400, detail="Chat number must be exactly 10 digits.")

    s = await session_repo.get_session_by_chat_number(chat_number)
    if not s or s.is_temporary:
        raise HTTPException(status_code=404, detail="Shared chat conversation not found.")

    messages = await session_repo.get_messages(s.id)
    summary = await session_repo.get_summary(s.id)

    return ApiResponse(
        success=True,
        message="Shared conversation retrieved.",
        data=SessionDetailSchema(
            id=s.id,
            title=s.title,
            mode=s.mode.value,
            selected_document_ids=s.selected_document_ids,
            chat_number=s.chat_number,
            created_at=s.created_at,
            updated_at=s.updated_at,
            messages=[
                MessageSchema(
                    id=m.id,
                    role=m.role,
                    content=m.content,
                    citations=m.citations,
                    created_at=m.created_at,
                )
                for m in messages
            ],
            summary=summary,
        ),
    )
