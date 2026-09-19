from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.api.dependencies.auth import get_current_user
from app.api.routes.auth import get_auth_service, UserResponse
from app.core.exceptions import (
    AuthenticationError,
    EntityNotFoundError,
    ValidationError,
)
from app.core.logging import LoggerFactory
from app.models.entities.user import UserEntity
from app.models.schemas.base import ApiResponse
from app.services.auth_service import AuthService

logger = LoggerFactory.create_logger("ProfileRoute")

router = APIRouter(prefix="/profile", tags=["Profile"])


class UpdateProfileRequest(BaseModel):
    name: str
    mobile: Optional[str] = None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str
    confirm_password: Optional[str] = None


@router.get("", response_model=ApiResponse[UserResponse])
async def get_profile(
    current_user: UserEntity = Depends(get_current_user),
):
    """Retrieve the current user's profile information."""
    return ApiResponse(
        success=True,
        message="Profile retrieved.",
        data=UserResponse(**current_user.to_profile_dict()),
    )


@router.patch("", response_model=ApiResponse[UserResponse])
async def update_profile(
    body: UpdateProfileRequest,
    current_user: UserEntity = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
):
    """Update profile information (name, mobile)."""
    try:
        updated = await auth_service.update_profile(
            user_id=current_user.id,
            name=body.name,
            mobile=body.mobile,
        )
        return ApiResponse(
            success=True,
            message="Profile updated successfully.",
            data=UserResponse(**updated.to_profile_dict()),
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/password", response_model=ApiResponse[dict])
async def change_password(
    body: ChangePasswordRequest,
    current_user: UserEntity = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
):
    """Update the user's password."""
    if body.confirm_password is not None and body.new_password != body.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New passwords do not match.",
        )

    try:
        await auth_service.change_password(
            user_id=current_user.id,
            current_password=body.current_password,
            new_password=body.new_password,
        )
        return ApiResponse(
            success=True,
            message="Password changed successfully.",
            data={"updated": True},
        )
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )
    except (ValidationError, EntityNotFoundError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
