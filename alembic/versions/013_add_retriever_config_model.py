# -*- coding: utf-8 -*-
"""
Add Retriever Configuration Model

This migration adds the AIRetrieverConfigDB table to support retriever configuration management:
- AIRetrieverConfigDB: Stores retriever configurations with embedding model and vector store settings

This model supports the new endpoints:
- GET /api/ai/retriever/configs
- POST /api/ai/retriever/configs
- DELETE /api/ai/retriever/configs/{config_id}
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import Index


# revision identifiers
revision = '013'
down_revision = '012'
branch_labels = None
depends_on = None


def upgrade():
    """Add retriever configuration table"""

    # Create ai_retriever_configs table
    op.create_table(
        'ai_retriever_configs',
        sa.Column('id', sa.String(50), primary_key=True, nullable=False),
        sa.Column('config_name', sa.String(255), nullable=False),
        sa.Column('retriever_type', sa.String(50), nullable=False),
        sa.Column('embedding_model', sa.String(255), nullable=False),
        sa.Column('vector_store_config', sa.JSON(), nullable=False),
        sa.Column('retrieval_params', sa.JSON(), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='active'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('config_metadata', sa.JSON(), nullable=True),
    )

    # Create indexes for ai_retriever_configs
    op.create_index('idx_ai_retriever_configs_status', 'ai_retriever_configs', ['status'])


def downgrade():
    """Remove retriever configuration table"""

    # Drop indexes for ai_retriever_configs
    op.drop_index('idx_ai_retriever_configs_status', table_name='ai_retriever_configs')

    # Drop ai_retriever_configs table
    op.drop_table('ai_retriever_configs')
