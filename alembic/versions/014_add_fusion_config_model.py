# -*- coding: utf-8 -*-
"""
Add Fusion Config Model

This migration adds database model for the AI Fusion module:
- AIFusionConfigDB: Stores fusion configuration for RAG retrieval

This model supports the new endpoints:
- GET /api/ai/fusion/configs
- POST /api/ai/fusion/configs
- DELETE /api/ai/fusion/configs/{config_id}
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import Index


# revision identifiers
revision = '014'
down_revision = '013'
branch_labels = None
depends_on = None


def upgrade():
    """Add fusion config table"""

    # Create ai_fusion_configs table
    op.create_table(
        'ai_fusion_configs',
        sa.Column('id', sa.String(50), primary_key=True, nullable=False),
        sa.Column('config_name', sa.String(255), nullable=False),
        sa.Column('fusion_strategy', sa.String(50), nullable=False),
        sa.Column('sources', sa.JSON(), nullable=False),
        sa.Column('weights', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='active'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('config_metadata', sa.JSON(), nullable=True),
    )

    # Create indexes for ai_fusion_configs
    op.create_index('idx_ai_fusion_configs_status', 'ai_fusion_configs', ['status'])


def downgrade():
    """Remove fusion config table"""

    # Drop indexes for ai_fusion_configs
    op.drop_index('idx_ai_fusion_configs_status', table_name='ai_fusion_configs')

    # Drop ai_fusion_configs table
    op.drop_table('ai_fusion_configs')
