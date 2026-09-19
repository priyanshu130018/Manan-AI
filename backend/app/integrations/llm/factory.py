from typing import Any
from app.core.config import get_settings
from app.core.exceptions import LLMError
from app.core.logging import LoggerFactory

logger = LoggerFactory.create_logger("LLMFactory")

STATIC_SUPPORTED_MODELS = {
    "gemini-3.6-flash": "gemini",
    "qwen3.8-27b": "qwen",
    "qwen2.5-72b": "qwen",
    "qwen-turbo": "qwen",
    "qwen-plus": "qwen",
    "qwen-max": "qwen",
}


class LLMFactory:
    @staticmethod
    def get_supported_models() -> dict[str, str]:
        settings = get_settings()
        models = dict(STATIC_SUPPORTED_MODELS)
        if settings.qwen_model:
            models[settings.qwen_model.strip()] = "qwen"
        if settings.llm_model and settings.llm_provider == "gemini":
            models[settings.llm_model.strip()] = "gemini"
        return models

    @staticmethod
    def get_chat_model(
        provider: str | None = None,
        model_name: str | None = None,
        temperature: float = 0.7,
    ) -> Any:
        settings = get_settings()
        supported_models = LLMFactory.get_supported_models()

        # Validate model_name against allowed models
        if model_name:
            norm_model = model_name.strip()
            if norm_model not in supported_models:
                raise LLMError(
                    f"Unsupported model '{model_name}'. Only 'gemini-3.6-flash' and '{settings.qwen_model or 'qwen3.8-27b'}' are supported.",
                    model=model_name,
                    provider=provider or settings.llm_provider,
                )

            expected_prov = supported_models[norm_model]
            if provider and provider.lower().strip() != expected_prov:
                raise LLMError(
                    f"Model '{model_name}' is a {expected_prov.capitalize()} model and cannot be used with provider '{provider}'.",
                    provider=provider,
                    model=model_name,
                )
            prov = expected_prov
            resolved_model = norm_model
        else:
            prov = (provider or settings.llm_provider).lower().strip()
            if prov == "gemini":
                resolved_model = (settings.llm_model or "gemini-3.6-flash").replace("models/", "")
            elif prov == "qwen":
                resolved_model = settings.qwen_model or "qwen3.8-27b"
            else:
                resolved_model = None

        if prov == "gemini":
            api_key = settings.google_api_key
            if not api_key:
                raise LLMError(
                    "Google API key is not configured for Gemini. Please set GOOGLE_API_KEY in your environment.",
                    provider="gemini",
                )
            model = resolved_model or "gemini-3.6-flash"
            try:
                from langchain_google_genai import ChatGoogleGenerativeAI
                return ChatGoogleGenerativeAI(
                    model=model,
                    google_api_key=api_key,
                    temperature=temperature,
                )
            except Exception as e:
                logger.error("Failed to initialize ChatGoogleGenerativeAI: %s", e)
                raise LLMError(
                    f"Gemini LLM initialization failed: {e}",
                    provider="gemini",
                    model=model,
                ) from e

        elif prov == "qwen":
            model = resolved_model or settings.qwen_model or "qwen3.8-27b"
            api_key = settings.qwen_api_key
            base_url = settings.qwen_base_url
            if not api_key or not base_url:
                raise LLMError(
                    "Qwen API is not configured. QWEN_API_KEY and QWEN_BASE_URL must be set in your environment.",
                    provider="qwen",
                    model=model,
                )
            logger.info("Initializing ChatQwen model='%s' at base_url='%s'", model, base_url)
            try:
                from app.integrations.qwen.client import ChatQwen, QwenClient
                client = QwenClient(api_key=api_key, base_url=base_url, model=model)
                return ChatQwen(client=client, model_name=model, temperature=temperature)
            except Exception as e:
                logger.error("Failed to initialize ChatQwen (model=%s): %s", model, e)
                raise LLMError(
                    f"Qwen LLM initialization failed for model '{model}': {e}",
                    provider="qwen",
                    model=model,
                ) from e

        else:
            raise LLMError(
                f"Unsupported LLM provider '{prov}'. Supported providers are 'gemini' and 'qwen'.",
                provider=prov,
            )


def get_llm(
    provider: str | None = None,
    model_name: str | None = None,
    temperature: float = 0.7,
) -> Any:
    """Convenience helper to obtain a configured LangChain Chat model."""
    return LLMFactory.get_chat_model(
        provider=provider,
        model_name=model_name,
        temperature=temperature,
    )
