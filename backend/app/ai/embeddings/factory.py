from app.ai.embeddings.base import BaseEmbedding
from app.ai.embeddings.gemini import GeminiEmbedding


class EmbeddingFactory:
    _instance: BaseEmbedding | None = None

    @classmethod
    def get_embedding(cls) -> BaseEmbedding:
        if cls._instance is None:
            cls._instance = GeminiEmbedding()

        return cls._instance