from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import List, Optional

from app.api.dependencies import get_memory_service
from app.api.dependencies.auth import get_current_user
from app.models.entities.user import UserEntity
from app.models.schemas.memory import MemoryCreateRequest, MemoryUpdateRequest, MemoryItem
from app.models.schemas.base import ApiResponse
from app.services.memory_service import MemoryService
from app.core.logging import LoggerFactory

logger = LoggerFactory.create_logger("MemoryRoute")

router = APIRouter(prefix="/memories", tags=["Memories"])


class DeleteResponse(BaseModel):
    success: bool
    message: str


@router.get("", response_model=ApiResponse[List[MemoryItem]])
async def list_memories(
    limit: int = 50,
    current_user: UserEntity = Depends(get_current_user),
    memory_service: MemoryService = Depends(get_memory_service),
):
    """Retrieve all stored long-term memories for current user."""
    memories = await memory_service.get_long_term_memories(user_id=current_user.id, limit=limit)
    items = [
        MemoryItem(
            id=m["id"],
            user_id=m.get("user_id"),
            content=m["content"],
            source_session_id=m.get("source_session_id"),
            created_at=str(m.get("created_at") or ""),
            updated_at=str(m.get("updated_at") or ""),
        )
        for m in memories
    ]
    return ApiResponse(
        success=True,
        message=f"Retrieved {len(items)} memories.",
        data=items,
    )


@router.post("", response_model=ApiResponse[MemoryItem])
async def create_memory(
    request: MemoryCreateRequest,
    current_user: UserEntity = Depends(get_current_user),
    memory_service: MemoryService = Depends(get_memory_service),
):
    """Manually add a long-term memory fact."""
    created = await memory_service.save_long_term_memory(
        content=request.content,
        user_id=current_user.id,
        session_id=request.source_session_id,
    )
    return ApiResponse(
        success=True,
        message="Memory created successfully.",
        data=MemoryItem(
            id=created["id"],
            user_id=created.get("user_id"),
            content=created["content"],
            source_session_id=created.get("source_session_id"),
            created_at=str(created.get("created_at") or ""),
            updated_at=str(created.get("updated_at") or ""),
        ),
    )


@router.patch("/{memory_id}", response_model=ApiResponse[MemoryItem])
async def update_memory(
    memory_id: str,
    request: MemoryUpdateRequest,
    current_user: UserEntity = Depends(get_current_user),
    memory_service: MemoryService = Depends(get_memory_service),
):
    """Manually update an existing long-term memory fact."""
    updated = await memory_service.update_long_term_memory(
        memory_id=memory_id,
        content=request.content,
        user_id=current_user.id,
    )
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Memory not found",
        )
    return ApiResponse(
        success=True,
        message="Memory updated successfully.",
        data=MemoryItem(
            id=updated["id"],
            user_id=updated.get("user_id"),
            content=updated["content"],
            source_session_id=updated.get("source_session_id"),
            created_at=str(updated.get("created_at") or ""),
            updated_at=str(updated.get("updated_at") or ""),
        ),
    )


@router.delete("/{memory_id}", response_model=ApiResponse[DeleteResponse])
async def delete_memory(
    memory_id: str,
    current_user: UserEntity = Depends(get_current_user),
    memory_service: MemoryService = Depends(get_memory_service),
):
    """Delete a specific long-term memory."""
    deleted = await memory_service.delete_long_term_memory(memory_id, user_id=current_user.id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Memory not found",
        )
    return ApiResponse(
        success=True,
        message="Memory deleted successfully.",
        data=DeleteResponse(success=True, message="Memory deleted successfully"),
    )


@router.delete("", response_model=ApiResponse[DeleteResponse])
async def clear_all_memories(
    current_user: UserEntity = Depends(get_current_user),
    memory_service: MemoryService = Depends(get_memory_service),
):
    """Clear all long-term memories for current user."""
    count = await memory_service.clear_long_term_memories(user_id=current_user.id)
    return ApiResponse(
        success=True,
        message=f"Cleared {count} memories.",
        data=DeleteResponse(success=True, message=f"Cleared {count} memories"),
    )
