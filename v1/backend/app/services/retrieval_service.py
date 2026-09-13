from collections import defaultdict
import asyncio

from app.core.config import get_settings
from app.integrations.embeddings import LocalEmbedding
from app.integrations.gemini.client import GeminiEmbedding
from app.models.entities.chunk import DocumentChunk
from app.repositories.document_repository import DocumentRepository
from app.repositories.vector_repository import VectorRepository


class RetrievalService:
    def __init__(
        self,
        vector_repo: VectorRepository | None = None,
        doc_repo: DocumentRepository | None = None,
        embedding: object | None = None,
        rrf_k: int = 60,
    ) -> None:
        settings = get_settings()
        self._vector_repo = vector_repo or VectorRepository()
        self._doc_repo = doc_repo or DocumentRepository()
        self._rrf_k = rrf_k

        if embedding is not None:
            self._embedding = embedding
        elif (settings.embedding_provider or "local").lower().strip() == "google":
            self._embedding = GeminiEmbedding()
        else:
            self._embedding = LocalEmbedding()

    async def retrieve_vectors(
        self,
        query: str,
        document_ids: list[str] | None = None,
        user_id: str | None = None,
        top_k: int = 10,
    ) -> list[DocumentChunk]:
        """Perform dense vector retrieval via embeddings and ChromaDB."""
        try:
            emb = await self._embedding.embed(query)
            filters = None
            conditions = []
            if user_id:
                conditions.append({"user_id": user_id})
            if document_ids:
                clean_ids = [d.strip() for d in document_ids if d and d.strip()]
                if len(clean_ids) == 1:
                    conditions.append({"document_id": clean_ids[0]})
                elif len(clean_ids) > 1:
                    conditions.append({"document_id": {"$in": clean_ids}})
            if len(conditions) == 1:
                filters = conditions[0]
            elif len(conditions) > 1:
                filters = {"$and": conditions}

            raw_chunks = await self._vector_repo.search(
                embedding=emb,
                top_k=top_k,
                filters=filters,
            )

            chunks: list[DocumentChunk] = []
            for rc in raw_chunks:
                chunks.append(DocumentChunk(
                    chunk_id=rc.id,
                    document_id=rc.metadata.get("document_id", ""),
                    filename=rc.metadata.get("filename", "Unknown"),
                    page_number=int(rc.metadata.get("page", 1)),
                    chunk_index=int(rc.metadata.get("chunk", 1)),
                    text=rc.document,
                    source_type=rc.metadata.get("source_type", "pdf"),
                    heading=rc.metadata.get("heading"),
                    score=rc.score,
                ))
            return chunks
        except Exception:
            return []

    async def retrieve_keywords(
        self,
        query: str,
        document_ids: list[str] | None = None,
        user_id: str | None = None,
        limit: int = 10,
    ) -> list[DocumentChunk]:
        """Perform sparse keyword retrieval."""
        return await self._doc_repo.search_fts(query=query, document_ids=document_ids, limit=limit)

    def reciprocal_rank_fusion(
        self,
        vector_candidates: list[DocumentChunk],
        keyword_candidates: list[DocumentChunk],
        top_k: int = 5,
    ) -> list[DocumentChunk]:
        """Combine dense and sparse candidates using Reciprocal Rank Fusion (RRF)."""
        scores: dict[str, float] = defaultdict(float)
        chunk_map: dict[str, DocumentChunk] = {}

        # Dense vector candidates rank
        for rank, chunk in enumerate(vector_candidates, start=1):
            key = f"{chunk.document_id}_{chunk.page_number}_{chunk.chunk_index}"
            chunk_map[key] = chunk
            scores[key] += 1.0 / (self._rrf_k + rank)

        # Keyword FTS candidates rank
        for rank, chunk in enumerate(keyword_candidates, start=1):
            key = f"{chunk.document_id}_{chunk.page_number}_{chunk.chunk_index}"
            if key not in chunk_map:
                chunk_map[key] = chunk
            scores[key] += 1.0 / (self._rrf_k + rank)

        # Sort by reciprocal rank score
        sorted_keys = sorted(scores.keys(), key=lambda k: scores[k], reverse=True)
        final_chunks: list[DocumentChunk] = []
        for key in sorted_keys[:top_k]:
            chunk = chunk_map[key]
            chunk.score = round(scores[key], 4)
            final_chunks.append(chunk)

        return final_chunks

    async def hybrid_retrieve(
        self,
        query: str,
        document_ids: list[str] | None = None,
        user_id: str | None = None,
        top_k: int = 5,
    ) -> list[DocumentChunk]:
        """Execute parallel dense + sparse retrieval and fuse with RRF."""
        vector_task = self.retrieve_vectors(query=query, document_ids=document_ids, user_id=user_id, top_k=top_k * 2)
        keyword_task = self.retrieve_keywords(query=query, document_ids=document_ids, user_id=user_id, limit=top_k * 2)

        vector_results, keyword_results = await asyncio.gather(vector_task, keyword_task)

        return self.reciprocal_rank_fusion(
            vector_candidates=vector_results,
            keyword_candidates=keyword_results,
            top_k=top_k,
        )


# Backward compatibility alias
HybridRetriever = RetrievalService
