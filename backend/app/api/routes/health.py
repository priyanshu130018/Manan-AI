from fastapi import APIRouter
from app.core.config import get_settings

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check():
    settings = get_settings()
    return {
        "success": True,
        "status": "healthy",
        "app_name": settings.app_name,
        "env": settings.env,
        "gemini_model": settings.gemini_model,
        "embedding_model": settings.embedding_model,
    }

