"""003_pgvector_hnsw

Revision ID: 003_pgvector_hnsw
Revises: 002_chunks_fts
Create Date: 2026-09-19 10:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = '003_pgvector_hnsw'
down_revision: Union[str, None] = '002_chunks_fts'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    # 2. Add embedding vector(384) and metadata JSONB columns to document_chunks
    op.execute(
        "ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS embedding vector(384);"
    )
    op.execute(
        "ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS metadata jsonb DEFAULT '{}'::jsonb;"
    )

    # 3. Create HNSW cosine distance index for vector search
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_document_chunks_embedding_hnsw
        ON document_chunks
        USING hnsw (embedding vector_cosine_ops);
        """
    )

    # 4. Composite index for fast document & user filtering
    op.create_index(
        'ix_document_chunks_doc_user',
        'document_chunks',
        ['document_id', 'user_id'],
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_index('ix_document_chunks_doc_user', table_name='document_chunks', if_exists=True)
    op.execute("DROP INDEX IF EXISTS ix_document_chunks_embedding_hnsw;")
    op.execute("ALTER TABLE document_chunks DROP COLUMN IF EXISTS metadata;")
    op.execute("ALTER TABLE document_chunks DROP COLUMN IF EXISTS embedding;")
