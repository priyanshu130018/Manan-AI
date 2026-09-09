from app.ai.vector_store.base import BaseVectorStore
from app.ai.vector_store.chroma import ChromaVectorStore


class VectorStoreFactory:
    _instance: BaseVectorStore | None = None

    @classmethod
    def get_vector_store(
        cls,
    ) -> BaseVectorStore:
        if cls._instance is None:
            cls._instance = ChromaVectorStore()

        return cls._instance