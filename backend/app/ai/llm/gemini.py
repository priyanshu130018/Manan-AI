from google import genai

from app.ai.llm.base import BaseLLM
from app.core.config import get_settings
from app.core.logger import LoggerFactory


class GeminiLLM(BaseLLM):
    def __init__(self) -> None:
        self._logger = LoggerFactory.create_logger(
            self.__class__.__name__
        )

        settings = get_settings()

        self._model = settings.gemini_model

        self._client = genai.Client(
            api_key=settings.google_api_key,
        )

    async def generate(
        self,
        prompt: str,
    ) -> str:
        try:
            response = self._client.models.generate_content(
                model=self._model,
                contents=prompt,
            )

            if not response.text:
                raise RuntimeError(
                    "Empty response received."
                )

            return response.text

        except Exception:
            self._logger.exception(
                "Gemini request failed."
            )
            raise