from typing import Any, Dict, List
from fastapi import APIRouter
from app.core.config import get_settings
from app.core.logging import LoggerFactory
from app.models.schemas.base import ApiResponse

logger = LoggerFactory.create_logger("ModelsRoute")
router = APIRouter(prefix="/llm", tags=["LLM Models"])


@router.get("/models", response_model=ApiResponse[Dict[str, Any]])
async def list_available_models():
    """Fetch available LLM models for Gemini and Qwen."""
    settings = get_settings()

    gemini_models = [
        {
            "value": settings.gemini_model or "gemini-3.6-flash",
            "label": "Gemini 3.6 Flash",
            "provider": "gemini",
        }
    ]

    qwen_models = [
        {
            "value": settings.qwen_model or "qwen3.8-27b",
            "label": "Qwen 3.8 27B",
            "provider": "qwen",
        }
    ]

    gemini_available = bool(settings.google_api_key and settings.google_api_key.strip())
    qwen_available = bool(
        settings.qwen_api_key
        and settings.qwen_api_key.strip()
        and settings.qwen_base_url
        and settings.qwen_base_url.strip()
    )

    current_provider = (settings.llm_provider or "gemini").lower().strip()
    default_model = (
        (settings.qwen_model or "qwen3.8-27b")
        if current_provider == "qwen"
        else (settings.gemini_model or "gemini-3.6-flash")
    )

    return ApiResponse(
        success=True,
        message="Available models retrieved successfully.",
        data={
            "gemini": {
                "available": gemini_available,
                "message": (
                    "Google Gemini API configured."
                    if gemini_available
                    else "GOOGLE_API_KEY is not configured."
                ),
                "models": gemini_models,
            },
            "qwen": {
                "available": qwen_available,
                "message": (
                    "Qwen API configured."
                    if qwen_available
                    else "Qwen API credentials not fully configured."
                ),
                "models": qwen_models,
            },
            "default_model": default_model,
            "default_provider": current_provider,
        },
    )
