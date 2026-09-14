from langchain_core.language_models.chat_models import BaseChatModel
from app.core.config import get_settings
from app.core.exceptions import LLMError
from app.core.logging import LoggerFactory

logger = LoggerFactory.create_logger("LLMFactory")


class LLMFactory:
    @staticmethod
    def get_chat_model(
        provider: str | None = None,
        model_name: str | None = None,
        temperature: float = 0.7,
    ) -> BaseChatModel:
        settings = get_settings()
        prov = (provider or settings.llm_provider or "gemini").lower().strip()

        if prov == "gemini":
            api_key = settings.google_api_key
            if not api_key:
                raise LLMError(
                    "Google API key is not configured for Gemini. Please set GOOGLE_API_KEY in your environment.",
                    provider="gemini",
                )
            model = model_name or settings.llm_model or "gemini-2.5-flash"
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
            model = model_name or settings.ollama_model or "llama3"
            base_url = settings.ollama_base_url or "http://localhost:11434"
            try:
                try:
                    from langchain_ollama import ChatOllama
                    return ChatOllama(
                        base_url=base_url,
                        model=model,
                        temperature=temperature,
                    )
                except ImportError:
                    from langchain_community.chat_models import ChatOllama
                    return ChatOllama(
                        base_url=base_url,
                        model=model,
                        temperature=temperature,
                    )
            except Exception as e:
                logger.error("Failed to initialize ChatOllama: %s", e)
                raise LLMError(
                    f"Ollama LLM initialization failed: {e}",
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
) -> BaseChatModel:
    """Convenience helper to obtain a configured LangChain Chat model."""
    return LLMFactory.get_chat_model(
        provider=provider,
        model_name=model_name,
        temperature=temperature,
    )
