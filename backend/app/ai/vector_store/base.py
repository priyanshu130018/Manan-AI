from abc import ABC
from abc import abstractmethod


class BaseVectorStore(ABC):
    @abstractmethod
    async def add(
        self,
        ids: list[str],
        documents: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict],
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def search(
        self,
        embedding: list[float],
        top_k: int,
        filters: dict[str, str] | None = None,
    ) -> list[dict]:
        raise NotImplementedError

    @abstractmethod
    async def list_documents(
        self,
    ) -> list[dict]:
        pass

    @abstractmethod
    async def delete_document(
        self,
        document_id: str,
    ) -> None:
        pass