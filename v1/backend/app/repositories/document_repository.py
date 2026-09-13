from typing import List, Optional
import psycopg
from app.core.config import get_settings
from app.models.entities.document import DocumentEntity
from app.models.entities.enums import DocumentStatus, SourceType

class DocumentRepository:
    def __init__(self, db_url: Optional[str] = None):
        self.db_url = db_url or get_settings().database_url

    def _get_connection(self):
        return psycopg.connect(self.db_url, autocommit=True)

    async def create(self, doc: DocumentEntity) -> None:
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO documents (id, filename, file_type, file_size, page_count, chunk_count, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        doc.document_id,
                        doc.original_filename,
                        doc.file_type,
                        doc.size_bytes,
                        doc.page_count,
                        doc.chunk_count,
                        doc.created_at,
                    ),
                )

    async def update(self, doc: DocumentEntity) -> None:
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE documents
                    SET filename = %s, file_type = %s, file_size = %s, page_count = %s, chunk_count = %s
                    WHERE id = %s
                    """,
                    (
                        doc.original_filename,
                        doc.file_type,
                        doc.size_bytes,
                        doc.page_count,
                        doc.chunk_count,
                        doc.document_id,
                    ),
                )

    async def get_by_id(self, document_id: str) -> Optional[DocumentEntity]:
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, filename, file_type, file_size, page_count, chunk_count, created_at
                    FROM documents WHERE id = %s
                    """,
                    (document_id,),
                )
                row = cur.fetchone()
                if not row:
                    return None
                return DocumentEntity(
                    document_id=row[0],
                    original_filename=row[1],
                    stored_filename=row[1],
                    source_type=SourceType(row[2]) if row[2] in [s.value for s in SourceType] else SourceType.TXT,
                    size_bytes=row[3],
                    page_count=row[4],
                    chunk_count=row[5],
                    created_at=row[6],
                )

    async def list_all(self) -> List[DocumentEntity]:
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, filename, file_type, file_size, page_count, chunk_count, created_at
                    FROM documents ORDER BY created_at DESC
                    """
                )
                rows = cur.fetchall()
                return [
                    DocumentEntity(
                        document_id=r[0],
                        original_filename=r[1],
                        stored_filename=r[1],
                        source_type=SourceType(r[2]) if r[2] in [s.value for s in SourceType] else SourceType.TXT,
                        size_bytes=r[3],
                        page_count=r[4],
                        chunk_count=r[5],
                        created_at=r[6],
                    )
                    for r in rows
                ]

    async def delete(self, document_id: str) -> None:
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM documents WHERE id = %s", (document_id,))

    async def get_total_storage_bytes(self) -> int:
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COALESCE(SUM(file_size), 0) FROM documents")
                row = cur.fetchone()
                return int(row[0]) if row else 0
