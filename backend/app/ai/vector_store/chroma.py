from collections import defaultdict

from chromadb import PersistentClient

from app.ai.vector_store.base import BaseVectorStore
from app.core.config import get_settings
from app.core.logger import LoggerFactory
from app.schemas.retrieval import RetrievedChunk


class ChromaVectorStore(BaseVectorStore):
    def __init__(self) -> None:
        self._logger = LoggerFactory.create_logger(
            self.__class__.__name__
        )

        settings = get_settings()

        self._collection = PersistentClient(
            path=settings.chroma_db,
        ).get_or_create_collection(
            name=settings.chroma_collection,
        )

    async def add(
        self,
        ids: list[str],
        documents: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict],
    ) -> None:
        try:
            self._collection.add(
                ids=ids,
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas,
            )

        except Exception:
            self._logger.exception(
                "Failed to add documents."
            )
            raise

    async def search(
        self,
        embedding: list[float],
        top_k: int,
        filters: dict[str, str] | None = None,
    ) -> list[RetrievedChunk]:
        try:
            result = self._collection.query(
                query_embeddings=[embedding],
                n_results=top_k,
                where=filters,
            )

            return [
                RetrievedChunk(
                    id=result["ids"][0][i],
                    document=result["documents"][0][i],
                    metadata=result["metadatas"][0][i],
                    distance=result["distances"][0][i],
                )
                for i in range(
                    len(result["ids"][0])
                )
            ]

        except Exception:
            self._logger.exception(
                "Vector search failed."
            )
            raise

    async def list_documents(
        self,
    ) -> list[dict]:
        try:
            result = self._collection.get(
                include=["metadatas"],
            )

            documents = defaultdict(
                lambda: {
                    "document_id": "",
                    "filename": "",
                    "chunks": 0,
                }
            )

            for metadata in result["metadatas"]:
                if metadata is None:
                    continue

                document_id = metadata.get(
                    "document_id"
                )

                if document_id is None:
                    continue

                document = documents[
                    document_id
                ]

                document["document_id"] = (
                    document_id
                )
                document["filename"] = metadata.get(
                    "filename",
                    "",
                )
                document["chunks"] += 1

            return list(
                documents.values()
            )

        except Exception:
            self._logger.exception(
                "Failed to list documents."
            )
            raise

    async def delete_document(
        self,
        document_id: str,
    ) -> None:
        try:
            self._collection.delete(
                where={
                    "document_id": document_id,
                },
            )

        except Exception:
            self._logger.exception(
                "Failed to delete document."
            )
            raise