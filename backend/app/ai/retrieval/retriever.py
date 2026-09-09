from app.ai.embeddings.factory import EmbeddingFactory
from app.ai.vector_store.factory import VectorStoreFactory
from app.schemas.retrieval import RetrievedChunk

class Retriever:
    def __init__(
        self,
    ) -> None:
        self._embedding = (
            EmbeddingFactory.get_embedding()
        )

        self._vector_store = (
            VectorStoreFactory.get_vector_store()
        )

    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        filters: dict[str, str] | None = None,
    ) -> list[RetrievedChunk]:
        embedding = await self._embedding.embed(
            query,
        )

        return await self._vector_store.search(
            embedding=embedding,
            top_k=top_k,
            filters=filters,
        )