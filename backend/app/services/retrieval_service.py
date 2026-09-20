from collections import defaultdict
import asyncio
from typing import Optional

from app.core.config import get_settings
from app.core.exceptions import EmbeddingError
from app.core.logging import LoggerFactory
from app.integrations.embeddings import HuggingFaceEmbedding
from app.integrations.gemini.client import GeminiEmbedding
from app.models.entities.chunk import DocumentChunk
from app.repositories.document_repository import DocumentRepository
from app.repositories.vector_repository import VectorRepository

logger = LoggerFactory.create_logger("RetrievalService")


class RetrievalService:
    """Hybrid RAG retrieval combining PostgreSQL pgvector HNSW search and PostgreSQL Full-Text Search."""

    def __init__(
        self,
        vector_repo: Optional[VectorRepository] = None,
        doc_repo: Optional[DocumentRepository] = None,
        embedding: Optional[object] = None,
        rrf_k: int = 60,
    ) -> None:
        settings = get_settings()
        self._vector_repo = vector_repo or VectorRepository()
        self._doc_repo = doc_repo or DocumentRepository()
        self._rrf_k = rrf_k

        provider = (settings.embedding_provider or "huggingface").lower().strip()
        if embedding is not None:
            self._embedding = embedding
        elif provider in ["huggingface", "hf"]:
            self._embedding = HuggingFaceEmbedding()
        elif provider in ["google", "gemini"]:
            self._embedding = GeminiEmbedding()
        else:
            raise EmbeddingError(
                f"Unsupported embedding provider '{settings.embedding_provider}'. Supported providers are: 'huggingface', 'google'"
            )

    async def retrieve_vectors(
        self,
        query: str,
        document_ids: Optional[list[str]] = None,
        user_id: Optional[str] = None,
        top_k: int = 10,
    ) -> list[DocumentChunk]:
        """Perform dense vector retrieval via embeddings and PostgreSQL pgvector HNSW search."""
        try:
            # 1. Ownership security verification: filter requested document_ids by user ownership
            clean_ids: list[str] = []
            if document_ids:
                raw_clean = [d.strip() for d in document_ids if d and d.strip()]
                if user_id:
                    user_docs = await self._doc_repo.list_all(user_id=user_id)
                    allowed_doc_ids = {d.document_id for d in user_docs}
                    clean_ids = [d for d in raw_clean if d in allowed_doc_ids]
                    if not clean_ids:
                        logger.warning(
                            "RAG Vector Retrieval blocked: requested document_ids %s do not belong to user_id '%s'.",
                            document_ids,
                            user_id,
                        )
                        return []
                else:
                    clean_ids = raw_clean

            # 2. Generate query embedding
            emb = await self._embedding.embed(query)
            emb_dim = len(emb) if isinstance(emb, list) else 0

            # 3. Search PostgreSQL pgvector using HNSW cosine index
            raw_chunks = await self._vector_repo.search(
                embedding=emb,
                top_k=top_k,
                document_ids=clean_ids if clean_ids else None,
                user_id=user_id,
            )

            chunks: list[DocumentChunk] = []
            for rc in raw_chunks:
                meta = rc.metadata or {}
                chunks.append(
                    DocumentChunk(
                        chunk_id=rc.id,
                        document_id=meta.get("document_id", ""),
                        filename=meta.get("filename", "Unknown"),
                        page_number=int(meta.get("page", 1) or 1),
                        chunk_index=int(meta.get("chunk", 0) or 0),
                        text=rc.document,
                        source_type=meta.get("source_type", "pdf"),
                        heading=meta.get("heading"),
                        score=rc.score,
                    )
                )

            logger.info(
                "RAG pgvector search: user_id='%s', requested_docs=%s, retrieved_chunks=%d, dim=%d",
                user_id or "anonymous",
                clean_ids,
                len(chunks),
                emb_dim,
            )
            return chunks
        except Exception as e:
            logger.exception(
                "Vector retrieval failed for user_id='%s', document_ids=%s: %s",
                user_id,
                document_ids,
                e,
            )
            return []

    async def retrieve_keywords(
        self,
        query: str,
        document_ids: Optional[list[str]] = None,
        user_id: Optional[str] = None,
        limit: int = 10,
    ) -> list[DocumentChunk]:
        """Perform sparse keyword retrieval using PostgreSQL Full-Text Search."""
        return await self._doc_repo.search_fts(query=query, document_ids=document_ids, user_id=user_id, limit=limit)

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
        document_ids: Optional[list[str]] = None,
        user_id: Optional[str] = None,
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
