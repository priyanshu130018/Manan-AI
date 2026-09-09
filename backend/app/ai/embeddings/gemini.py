from google import genai

from app.ai.embeddings.base import BaseEmbedding
from app.core.config import get_settings
from app.core.logger import LoggerFactory


class GeminiEmbedding(BaseEmbedding):
    def __init__(self) -> None:
        self._logger = LoggerFactory.create_logger(
            self.__class__.__name__
        )

        settings = get_settings()

        self._client = genai.Client(
            api_key=settings.google_api_key,
        ).aio

        self._model = settings.embedding_model

    async def embed(
        self,
        text: str,
    ) -> list[float]:
        try:
            response = await self._client.models.embed_content(
                model=self._model,
                contents=text,
            )

            return response.embeddings[0].values

        except Exception:
            self._logger.exception(
                "Embedding generation failed."
            )
            raise