from app.ai.llm.base import BaseLLM
from app.ai.llm.gemini import GeminiLLM


class LLMFactory:
    _instance: BaseLLM | None = None

    @classmethod
    def get_llm(cls) -> BaseLLM:
        if cls._instance is None:
            cls._instance = GeminiLLM()

        return cls._instance