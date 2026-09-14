from typing import Any
from chromadb import PersistentClient
from app.core.config import get_settings
from app.core.logging import LoggerFactory
from app.models.schemas.retrieval import RetrievedChunk

logger = LoggerFactory.create_logger("VectorRepository")

_shared_chroma_client = None


class VectorRepository:
    def __init__(self, client: Any = None) -> None:
        global _shared_chroma_client
        settings = get_settings()
        if client is not None:
            self._client = client
        else:
            if _shared_chroma_client is None:
                try:
                    _shared_chroma_client = PersistentClient(path=settings.chroma_dir)
                except Exception:
                    import chromadb
                    _shared_chroma_client = chromadb.Client()
            self._client = _shared_chroma_client

        try:
            self._collection = self._client.get_or_create_collection(
                name=settings.chroma_collection,
                metadata={"hnsw:space": "cosine"},
            )
        except Exception:
            self._collection = self._client.get_collection(name=settings.chroma_collection)


    async def add(
        self,
        ids: list[str],
        documents: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict[str, Any]],
    ) -> None:
        try:
            self._collection.add(
                ids=ids,
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas,
            )
        except Exception as e:
            logger.exception("Failed to insert documents into ChromaDB: %s", str(e))
            raise e

    async def search(
        self,
        embedding: list[float],
        top_k: int = 5,
        filters: dict[str, Any] | None = None,
    ) -> list[RetrievedChunk]:
        try:
            total = self._collection.count()
            if total == 0:
                return []
            k = min(top_k, total)
            kwargs: dict[str, Any] = {
                "query_embeddings": [embedding],
                "n_results": k,
            }
            if filters:
                kwargs["where"] = filters

            res = self._collection.query(**kwargs)
            if not res or not res.get("ids") or not res["ids"][0]:
                return []

            chunks: list[RetrievedChunk] = []
            for i in range(len(res["ids"][0])):
                dist = res["distances"][0][i] if res.get("distances") else 0.0
                score = round(1.0 - dist, 4) if dist is not None else 0.0
                chunks.append(RetrievedChunk(
                    id=res["ids"][0][i],
                    document=res["documents"][0][i] if res.get("documents") else "",
                    metadata=res["metadatas"][0][i] if res.get("metadatas") else {},
                    distance=dist,
                    score=score,
                ))
            return chunks
        except Exception as e:
            logger.exception("Chroma vector search failed: %s", str(e))
            return []

    async def delete_document(self, document_id: str) -> None:
        try:
            self._collection.delete(where={"document_id": document_id})
        except Exception as e:
            logger.warning("Could not delete Chroma vectors for document_id %s: %s", document_id, str(e))


# Backward compatibility alias
ChromaVectorStore = VectorRepository
