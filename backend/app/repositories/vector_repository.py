import json
from datetime import datetime, timezone
from typing import Any, Optional

from app.core.config import get_settings
from app.core.logging import LoggerFactory
from app.models.database import PostgresDatabase, get_database
from app.models.schemas.retrieval import RetrievedChunk

logger = LoggerFactory.create_logger("VectorRepository")


class VectorRepository:
    """PostgreSQL + pgvector repository for semantic chunk storage and HNSW vector search."""

    def __init__(self, db: Optional[PostgresDatabase] = None) -> None:
        self._db = db or get_database()
        self._settings = get_settings()

    @staticmethod
    def _format_vector(vector: list[float]) -> str:
        """Format a list of floats as a PostgreSQL vector literal string '[v1,v2,...]'."""
        return "[" + ",".join(f"{x:.6f}" for x in vector) + "]"

    async def add(
        self,
        ids: list[str],
        documents: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict[str, Any]],
        user_id: Optional[str] = None,
    ) -> None:
        """Atomically persist chunks, embeddings, and metadata into PostgreSQL document_chunks table."""
        if not ids:
            return

        now = datetime.now(timezone.utc)
        settings = self._settings
        expected_dim = settings.embedding_dimension

        with self._db._db_lock, self._db.get_connection() as conn:
            with conn.cursor() as cur:
                for chunk_id, text, emb, meta in zip(ids, documents, embeddings, metadatas):
                    if len(emb) != expected_dim:
                        raise ValueError(
                            f"Embedding dimension mismatch for chunk '{chunk_id}': "
                            f"expected {expected_dim}, got {len(emb)}"
                        )

                    doc_id = meta.get("document_id", "")
                    uid = user_id or meta.get("user_id")
                    fname = meta.get("filename", "Unknown")
                    page_num = int(meta.get("page", 1) or 1)
                    chunk_idx = int(meta.get("chunk", 0) or 0)
                    src_type = meta.get("source_type", "pdf")
                    vec_str = self._format_vector(emb)
                    meta_json = json.dumps(meta)

                    cur.execute(
                        """
                        INSERT INTO document_chunks 
                        (chunk_id, document_id, user_id, filename, page_number, chunk_index, text, source_type, created_at, embedding, metadata)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::vector, %s::jsonb)
                        ON CONFLICT (chunk_id) DO UPDATE SET
                            text = EXCLUDED.text,
                            filename = EXCLUDED.filename,
                            page_number = EXCLUDED.page_number,
                            chunk_index = EXCLUDED.chunk_index,
                            embedding = EXCLUDED.embedding,
                            metadata = EXCLUDED.metadata,
                            created_at = EXCLUDED.created_at;
                        """,
                        (
                            chunk_id,
                            doc_id,
                            uid,
                            fname,
                            page_num,
                            chunk_idx,
                            text,
                            src_type,
                            now,
                            vec_str,
                            meta_json,
                        ),
                    )
        logger.info("Successfully persisted %d vector chunks to PostgreSQL pgvector.", len(ids))

    async def search(
        self,
        embedding: list[float],
        top_k: int = 5,
        document_ids: Optional[list[str]] = None,
        user_id: Optional[str] = None,
    ) -> list[RetrievedChunk]:
        """Perform HNSW cosine distance vector similarity search using PostgreSQL pgvector."""
        if not embedding:
            return []

        vec_str = self._format_vector(embedding)
        conditions = ["embedding IS NOT NULL"]
        params: list[Any] = [vec_str]

        if user_id:
            conditions.append("user_id = %s")
            params.append(user_id)

        if document_ids:
            clean_ids = [d.strip() for d in document_ids if d and d.strip()]
            if clean_ids:
                conditions.append("document_id = ANY(%s)")
                params.append(clean_ids)

        where_clause = " AND ".join(conditions)
        sql = f"""
        SELECT chunk_id, document_id, filename, page_number, chunk_index, text, source_type, metadata,
               (1 - (embedding <=> %s::vector)) AS score,
               (embedding <=> %s::vector) AS distance
        FROM document_chunks
        WHERE {where_clause}
        ORDER BY embedding <=> %s::vector
        LIMIT %s;
        """
        # params: [vec_str, vec_str, ...conditions..., vec_str, top_k]
        full_params = [vec_str, vec_str] + params[1:] + [vec_str, top_k]

        with self._db._db_lock, self._db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, full_params)
                rows = cur.fetchall()

        results: list[RetrievedChunk] = []
        for r in rows:
            meta = r.get("metadata") or {}
            if isinstance(meta, str):
                try:
                    meta = json.loads(meta)
                except Exception:
                    meta = {}
            # Populate essential metadata keys if absent
            meta.setdefault("document_id", r.get("document_id"))
            meta.setdefault("filename", r.get("filename"))
            meta.setdefault("page", r.get("page_number"))
            meta.setdefault("chunk", r.get("chunk_index"))
            meta.setdefault("source_type", r.get("source_type"))

            score = float(r.get("score") or 0.0)
            distance = float(r.get("distance") or 0.0)

            results.append(
                RetrievedChunk(
                    id=r["chunk_id"],
                    document=r["text"],
                    metadata=meta,
                    distance=distance,
                    score=round(score, 4),
                )
            )
        return results

    async def delete_document(self, document_id: str, user_id: Optional[str] = None) -> None:
        """Delete all chunks and vectors for a document."""
        with self._db._db_lock, self._db.get_connection() as conn:
            with conn.cursor() as cur:
                if user_id:
                    cur.execute(
                        "DELETE FROM document_chunks WHERE document_id = %s AND user_id = %s;",
                        (document_id, user_id),
                    )
                else:
                    cur.execute(
                        "DELETE FROM document_chunks WHERE document_id = %s;",
                        (document_id,),
                    )
        logger.info("Deleted vector chunks for document_id %s (user_id=%s).", document_id, user_id)
