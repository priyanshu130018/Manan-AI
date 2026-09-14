"""002_chunks_fts

Revision ID: 002_chunks_fts
Revises: 001_v2_schema
Create Date: 2026-09-14 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '002_chunks_fts'
down_revision: Union[str, None] = '001_v2_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. document_chunks table
    op.create_table(
        'document_chunks',
        sa.Column('chunk_id', sa.String(64), primary_key=True),
        sa.Column('document_id', sa.String(36), sa.ForeignKey('documents.document_id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=True),
        sa.Column('filename', sa.String(255), nullable=False),
        sa.Column('page_number', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('chunk_index', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('source_type', sa.String(50), nullable=False, server_default='pdf'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_document_chunks_document_id', 'document_chunks', ['document_id'])
    op.create_index('ix_document_chunks_user_id', 'document_chunks', ['user_id'])

    # 2. PostgreSQL Full-Text Search index
    op.execute(
        "CREATE INDEX ix_document_chunks_fts ON document_chunks USING gin(to_tsvector('english', text));"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_document_chunks_fts;")
    op.drop_table('document_chunks')
