"""004_cloudinary_storage

Revision ID: 004_cloudinary_storage
Revises: 003_pgvector_hnsw
Create Date: 2026-09-19 16:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '004_cloudinary_storage'
down_revision: Union[str, None] = '003_pgvector_hnsw'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('documents', sa.Column('cloudinary_public_id', sa.String(255), nullable=True))
    op.add_column('documents', sa.Column('cloudinary_secure_url', sa.Text(), nullable=True))
    op.add_column('documents', sa.Column('cloudinary_resource_type', sa.String(50), nullable=True))


def downgrade() -> None:
    op.drop_column('documents', 'cloudinary_resource_type')
    op.drop_column('documents', 'cloudinary_secure_url')
    op.drop_column('documents', 'cloudinary_public_id')
