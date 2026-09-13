from fastapi import APIRouter
from app.models.schemas.base import ApiResponse

router = APIRouter(prefix="/health", tags=["Health"])

@router.get("")
async def health_check():
    return ApiResponse(
        success=True,
        message="Manan AI V1 is running healthy.",
        data={"version": "1.0.0", "status": "healthy", "mode": "anonymous-gemini"},
    )
