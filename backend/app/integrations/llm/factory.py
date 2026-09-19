from typing import Any
from app.core.config import get_settings
from app.core.exceptions import LLMError
from app.core.logging import LoggerFactory

logger = LoggerFactory.create_logger("LLMFactory")

OBSOLETE_MODELS = {
    "gemini-2.5-flash",
    "gemini-2.5-pro",
    "gemini-3-pro",
    "philatest",
    "deepseek-coder:latest",
    "phi3:latest",
    "qwen3.8-27b",
    "qwen3-coder:480b",
    "qwen3-coder:480b-cloud",
    "unknown-model-xyz",
}


class LLMFactory:
    @staticmethod
    def get_supported_models() -> dict[str, str]:
        settings = get_settings()
        models = {
            "gemini-3.6-flash": "gemini",
        }
        if settings.ollama_model:
            models[settings.ollama_model.strip()] = "ollama"
        return models

    @staticmethod
    def get_chat_model(
        provider: str | None = None,
        model_name: str | None = None,
        temperature: float = 0.7,
    ) -> Any:
        settings = get_settings()

        # Reject explicitly obsolete models
        if model_name:
            norm_model = model_name.strip()
            if norm_model in OBSOLETE_MODELS:
                raise LLMError(
                    f"Unsupported model '{model_name}'.",
                    model=model_name,
                    provider=provider or settings.llm_provider,
                )

        # Determine provider and model
        if model_name:
            norm_model = model_name.strip()
            if norm_model == "gemini-3.6-flash":
                expected_prov = "gemini"
            elif (
                norm_model == settings.ollama_model
                or any(k in norm_model.lower() for k in ("gpt", "oss", "gemma", "nemotron", "qwen", "llama", "cloud"))
            ):
                expected_prov = "ollama"
            else:
                # Check if it's explicitly supported
                supported = LLMFactory.get_supported_models()
                if norm_model in supported:
                    expected_prov = supported[norm_model]
                else:
                    raise LLMError(
                        f"Unsupported model '{model_name}'.",
                        model=model_name,
                        provider=provider or settings.llm_provider,
                    )

            if provider and provider.lower().strip() != expected_prov:
                prov_title = "Gemini" if expected_prov == "gemini" else "Ollama Cloud"
                raise LLMError(
                    f"Model '{model_name}' is a {prov_title} model and cannot be used with provider '{provider}'.",
                    provider=provider,
                    model=model_name,
                )
            prov = expected_prov
            resolved_model = norm_model
        else:
            prov = (provider or settings.llm_provider).lower().strip()
            if prov == "gemini":
                resolved_model = (settings.llm_model or "gemini-3.6-flash").replace("models/", "")
            elif prov == "ollama":
                resolved_model = settings.ollama_model or "gpt-oss:120b"
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

        elif prov == "ollama":
            api_key = settings.ollama_api_key
            if not api_key:
                raise LLMError(
                    "Ollama API key is not configured for Ollama Cloud. Please set OLLAMA_API_KEY in your environment.",
                    provider="ollama",
                )
            model = resolved_model or settings.ollama_model or "gpt-oss:120b"
            raw_url = (settings.ollama_base_url or "https://ollama.com").rstrip("/")
            if raw_url.endswith("/v1"):
                raw_url = raw_url[:-3].rstrip("/")
            base_url = raw_url or "https://ollama.com"
            logger.info("Initializing ChatOllama model='%s' at base_url='%s'", model, base_url)
            try:
                from langchain_ollama import ChatOllama
                return ChatOllama(
                    model=model,
                    base_url=base_url,
                    client_kwargs={"headers": {"Authorization": f"Bearer {api_key}"}},
                    temperature=temperature,
                )
            except Exception as e:
                logger.error("Failed to initialize ChatOllama (model=%s): %s", model, e)
                raise LLMError(
                    f"Ollama Cloud LLM initialization failed for model '{model}': {e}",
                    provider="ollama",
                    model=model,
                ) from e

        else:
            raise LLMError(
                f"Unsupported LLM provider '{prov}'. Supported providers are 'gemini' and 'ollama'.",
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
