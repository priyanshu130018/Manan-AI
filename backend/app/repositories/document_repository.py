from datetime import datetime, timezone
from app.models.database import PostgresDatabase, get_database
from app.models.entities.document import DocumentEntity
from app.models.entities.chunk import DocumentChunk
from app.models.entities.enums import DocumentStatus, SourceType


class DocumentRepository:
    def __init__(self, db: PostgresDatabase | None = None) -> None:
        self._db = db or get_database()

    async def create(self, document: DocumentEntity) -> None:
        c_at = datetime.fromtimestamp(document.created_at, timezone.utc) if isinstance(document.created_at, (int, float)) and document.created_at > 0 else datetime.now(timezone.utc)
        with self._db._db_lock, self._db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                INSERT INTO documents 
                (document_id, user_id, original_filename, stored_filename, mime_type, size_bytes, status, created_at, page_count, chunk_count, source_type, processing_error, cloudinary_public_id, cloudinary_secure_url, cloudinary_resource_type)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (document_id) DO UPDATE SET
                    user_id = EXCLUDED.user_id,
                    original_filename = EXCLUDED.original_filename,
                    stored_filename = EXCLUDED.stored_filename,
                    mime_type = EXCLUDED.mime_type,
                    size_bytes = EXCLUDED.size_bytes,
                    status = EXCLUDED.status,
                    created_at = EXCLUDED.created_at,
                    page_count = EXCLUDED.page_count,
                    chunk_count = EXCLUDED.chunk_count,
                    source_type = EXCLUDED.source_type,
                    processing_error = EXCLUDED.processing_error,
                    cloudinary_public_id = EXCLUDED.cloudinary_public_id,
                    cloudinary_secure_url = EXCLUDED.cloudinary_secure_url,
                    cloudinary_resource_type = EXCLUDED.cloudinary_resource_type;
                """, (
                    document.document_id,
                    document.user_id,
                    document.original_filename,
                    document.stored_filename,
                    document.mime_type,
                    document.size_bytes,
                    document.status.value,
                    c_at,
                    document.page_count,
                    document.chunk_count,
                    document.source_type.value,
                    document.processing_error,
                    document.cloudinary_public_id,
                    document.cloudinary_secure_url,
                    document.cloudinary_resource_type,
                ))

    def _row_to_entity(self, row: dict) -> DocumentEntity:
        c_at = row.get("created_at")
        return DocumentEntity(
            document_id=row["document_id"],
            user_id=row.get("user_id"),
            original_filename=row["original_filename"],
            stored_filename=row["stored_filename"],
            mime_type=row["mime_type"],
            size_bytes=row["size_bytes"],
            status=DocumentStatus(row["status"]),
            created_at=c_at.timestamp() if isinstance(c_at, datetime) else float(c_at or 0.0),
            page_count=row["page_count"],
            chunk_count=row["chunk_count"],
            source_type=SourceType(row["source_type"]),
            processing_error=row["processing_error"],
            cloudinary_public_id=row.get("cloudinary_public_id"),
            cloudinary_secure_url=row.get("cloudinary_secure_url"),
            cloudinary_resource_type=row.get("cloudinary_resource_type"),
        )

    async def get_by_id(self, document_id: str, user_id: str | None = None) -> DocumentEntity | None:
        with self._db._db_lock, self._db.get_connection() as conn:
            with conn.cursor() as cur:
                if user_id:
                    cur.execute("SELECT * FROM documents WHERE document_id = %s AND user_id = %s;", (document_id, user_id))
                else:
                    cur.execute("SELECT * FROM documents WHERE document_id = %s;", (document_id,))
                row = cur.fetchone()
                if not row:
                    return None
                return self._row_to_entity(dict(row))

    async def list_all(self, user_id: str | None = None) -> list[DocumentEntity]:
        with self._db._db_lock, self._db.get_connection() as conn:
            with conn.cursor() as cur:
                if user_id:
                    cur.execute("SELECT * FROM documents WHERE user_id = %s ORDER BY created_at DESC;", (user_id,))
                else:
                    cur.execute("SELECT * FROM documents ORDER BY created_at DESC;")
                rows = cur.fetchall()
                return [self._row_to_entity(dict(row)) for row in rows]

    async def update(self, document: DocumentEntity) -> None:
        await self.create(document)

    async def delete(self, document_id: str, user_id: str | None = None) -> None:
        with self._db._db_lock, self._db.get_connection() as conn:
            with conn.cursor() as cur:
                if user_id:
                    cur.execute("DELETE FROM documents WHERE document_id = %s AND user_id = %s;", (document_id, user_id))
                else:
                    cur.execute("DELETE FROM documents WHERE document_id = %s;", (document_id,))

    async def get_total_storage_bytes(self, user_id: str | None = None) -> int:
        with self._db._db_lock, self._db.get_connection() as conn:
            with conn.cursor() as cur:
                if user_id:
                    cur.execute("SELECT COALESCE(SUM(size_bytes), 0) AS total_bytes FROM documents WHERE user_id = %s;", (user_id,))
                else:
                    cur.execute("SELECT COALESCE(SUM(size_bytes), 0) AS total_bytes FROM documents;")
                row = cur.fetchone()
                return int(row["total_bytes"]) if row else 0

    async def index_chunks_fts(self, chunks: list[DocumentChunk], user_id: str | None = None) -> None:
        if not chunks:
            return
        now = datetime.now(timezone.utc)
        with self._db._db_lock, self._db.get_connection() as conn:
            with conn.cursor() as cur:
                for c in chunks:
                    cur.execute(
                        """
                        INSERT INTO document_chunks (chunk_id, document_id, user_id, filename, page_number, chunk_index, text, source_type, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (chunk_id) DO UPDATE SET
                            text = EXCLUDED.text,
                            filename = EXCLUDED.filename,
                            page_number = EXCLUDED.page_number,
                            chunk_index = EXCLUDED.chunk_index;
                        """,
                        (
                            c.chunk_id,
                            c.document_id,
                            user_id,
                            c.filename,
                            c.page_number,
                            c.chunk_index,
                            c.text,
                            c.source_type,
                            now,
                        ),
                    )

    async def search_fts(self, query: str, document_ids: list[str] | None = None, user_id: str | None = None, limit: int = 10) -> list[DocumentChunk]:
        if not query or not query.strip():
            return []
        with self._db._db_lock, self._db.get_connection() as conn:
            with conn.cursor() as cur:
                conditions = ["to_tsvector('english', text) @@ plainto_tsquery('english', %s)"]
                params: list = [query]
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
                SELECT chunk_id, document_id, filename, page_number, chunk_index, text, source_type,
                       ts_rank(to_tsvector('english', text), plainto_tsquery('english', %s)) AS rank
                FROM document_chunks
                WHERE {where_clause}
                ORDER BY rank DESC
                LIMIT %s;
                """
                params_full = [query] + params + [limit]
                cur.execute(sql, params_full)
                rows = cur.fetchall()
                results: list[DocumentChunk] = []
                for row in rows:
                    results.append(
                        DocumentChunk(
                            chunk_id=row["chunk_id"],
                            document_id=row["document_id"],
                            filename=row["filename"],
                            page_number=row["page_number"],
                            chunk_index=row["chunk_index"],
                            text=row["text"],
                            source_type=row.get("source_type", "pdf"),
                            score=float(row.get("rank") or 0.0),
                        )
                    )
                return results

    async def delete_chunks_fts(self, document_id: str, user_id: str | None = None) -> None:
        with self._db._db_lock, self._db.get_connection() as conn:
            with conn.cursor() as cur:
                if user_id:
                    cur.execute("DELETE FROM document_chunks WHERE document_id = %s AND user_id = %s;", (document_id, user_id))
                else:
                    cur.execute("DELETE FROM document_chunks WHERE document_id = %s;", (document_id,))



