from typing import Any, Dict
from fastapi import APIRouter
from app.core.config import get_settings
from app.core.logging import LoggerFactory
from app.models.schemas.base import ApiResponse

logger = LoggerFactory.create_logger("ModelsRoute")
router = APIRouter(prefix="/llm", tags=["LLM Models"])


@router.get("/models", response_model=ApiResponse[Dict[str, Any]])
async def list_available_models():
    """Fetch available LLM models for Gemini and Ollama Cloud."""
    settings = get_settings()

    gemini_models = [
        {
            "value": settings.gemini_model or "gemini-3.6-flash",
            "label": "Gemini 3.6 Flash",
            "provider": "gemini",
        }
    ]

    ollama_model_val = settings.ollama_model or "gpt-oss:120b"
    if "gpt-oss:120b" in ollama_model_val.lower():
        ollama_label = "GPT-OSS 120B (Ollama Cloud)"
    elif "gpt-oss:20b" in ollama_model_val.lower():
        ollama_label = "GPT-OSS 20B (Ollama Cloud)"
    elif "gemma4" in ollama_model_val.lower():
        ollama_label = "Gemma 4 31B (Ollama Cloud)"
    elif "qwen3-coder" in ollama_model_val.lower():
        ollama_label = "Qwen 3 Coder 480B (Ollama Cloud)"
    else:
        ollama_label = f"{ollama_model_val} (Ollama Cloud)"

    ollama_models = [
        {
            "value": ollama_model_val,
            "label": ollama_label,
            "provider": "ollama",
        }
    ]

    gemini_available = bool(settings.google_api_key and settings.google_api_key.strip())
    ollama_available = bool(settings.ollama_api_key and settings.ollama_api_key.strip())

    current_provider = (settings.llm_provider or "gemini").lower().strip()
    if current_provider not in {"gemini", "ollama"}:
        current_provider = "gemini"

    default_model = (
        ollama_model_val
        if current_provider == "ollama"
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
            "ollama": {
                "available": ollama_available,
                "message": (
                    f"Ollama Cloud API configured ({settings.ollama_base_url})."
                    if ollama_available
                    else "OLLAMA_API_KEY is not configured."
                ),
                "models": ollama_models,
            },
            "default_model": default_model,
            "default_provider": current_provider,
        },
    )
