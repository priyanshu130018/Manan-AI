import uuid
from fastapi import APIRouter, HTTPException, Depends
from app.api.dependencies import get_session_repository
from app.repositories.session_repository import SessionRepository
from app.models.entities.enums import AppMode
from app.models.schemas.base import ApiResponse
from app.models.schemas.session import (
    SessionSchema,
    SessionDetailSchema,
    MessageSchema,
    CreateSessionRequest,
    UpdateSessionRequest,
)

router = APIRouter(prefix="/sessions", tags=["Sessions"])

@router.get("", response_model=ApiResponse[list[SessionSchema]])
async def list_sessions(
    session_repo: SessionRepository = Depends(get_session_repository),
):
    sessions = await session_repo.list_sessions()
    return ApiResponse(
        success=True,
        message="Retrieved sessions.",
        data=[
            SessionSchema(
                id=s.id,
                title=s.title,
                mode=s.mode.value,
                selected_document_ids=s.selected_document_ids,
                chat_number=s.chat_number,
                created_at=s.created_at,
                updated_at=s.updated_at,
            )
            for s in sessions
        ],
    )

@router.post("", response_model=ApiResponse[SessionSchema])
async def create_session(
    request: CreateSessionRequest,
    session_repo: SessionRepository = Depends(get_session_repository),
):
    new_id = request.id or str(uuid.uuid4())
    s = await session_repo.get_or_create_session(
        session_id=new_id,
        title=request.title,
        mode=request.mode,
        chat_number=request.chat_number,
    )
    s.selected_document_ids = request.selected_document_ids
    if request.chat_number:
        s.chat_number = request.chat_number
    await session_repo.update_session(s)

    if request.messages:
        from app.models.entities.message import MessageEntity
        for m in request.messages:
            await session_repo.add_message(
                MessageEntity(
                    id=m.id,
                    session_id=new_id,
                    role=m.role,
                    content=m.content,
                    citations=m.citations,
                    created_at=m.created_at,
                )
            )

    return ApiResponse(
        success=True,
        message="Session created.",
        data=SessionSchema(
            id=s.id,
            title=s.title,
            mode=s.mode.value,
            selected_document_ids=s.selected_document_ids,
            chat_number=s.chat_number,
            created_at=s.created_at,
            updated_at=s.updated_at,
        ),
    )

@router.get("/by-number/{chat_number}", response_model=ApiResponse[SessionDetailSchema])
async def get_session_by_number(
    chat_number: str,
    session_repo: SessionRepository = Depends(get_session_repository),
):
    if not chat_number.isdigit() or len(chat_number) != 10:
        raise HTTPException(status_code=400, detail="Chat number must be exactly 10 digits.")

    s = await session_repo.get_session_by_chat_number(chat_number)
    if not s:
        raise HTTPException(status_code=404, detail="Chat not found.")

    messages = await session_repo.get_messages(s.id)
    summary = await session_repo.get_summary(s.id)

    return ApiResponse(
        success=True,
        message="Session details loaded.",
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

@router.get("/{session_id}", response_model=ApiResponse[SessionDetailSchema])
async def get_session(
    session_id: str,
    session_repo: SessionRepository = Depends(get_session_repository),
):
    s = await session_repo.get_session(session_id)
    if not s:
        raise HTTPException(status_code=404, detail="Session not found.")

    messages = await session_repo.get_messages(session_id)
    summary = await session_repo.get_summary(session_id)

    return ApiResponse(
        success=True,
        message="Session details loaded.",
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

@router.patch("/{session_id}", response_model=ApiResponse[SessionSchema])
async def update_session(
    session_id: str,
    request: UpdateSessionRequest,
    session_repo: SessionRepository = Depends(get_session_repository),
):
    s = await session_repo.get_session(session_id)
    if not s:
        raise HTTPException(status_code=404, detail="Session not found.")
    if request.title is not None:
        s.title = request.title
    if request.mode is not None:
        s.mode = AppMode(request.mode) if request.mode in ["chat", "study"] else AppMode.CHAT
    if request.selected_document_ids is not None:
        s.selected_document_ids = request.selected_document_ids
    if request.chat_number is not None:
        s.chat_number = request.chat_number
    await session_repo.update_session(s)
    return ApiResponse(
        success=True,
        message="Session updated.",
        data=SessionSchema(
            id=s.id,
            title=s.title,
            mode=s.mode.value,
            selected_document_ids=s.selected_document_ids,
            chat_number=s.chat_number,
            created_at=s.created_at,
            updated_at=s.updated_at,
        ),
    )

@router.delete("/{session_id}", response_model=ApiResponse[None])
async def delete_session(
    session_id: str,
    session_repo: SessionRepository = Depends(get_session_repository),
):
    await session_repo.delete_session(session_id)
    return ApiResponse(
        success=True,
        message="Session deleted.",
        data=None,
    )
