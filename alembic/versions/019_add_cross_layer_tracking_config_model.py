# -*- coding: utf-8 -*-
"""
Add Cross-Layer Tracking Configuration Model

This migration adds the AICrossLayerTrackingConfigDB table to support cross-layer tracking configuration management:
- AICrossLayerTrackingConfigDB: Stores cross-layer tracking configurations with layer, sampling rate, and retention settings

This model supports the new endpoints:
- GET /api/ai/cross-layer-tracking/configs
- POST /api/ai/cross-layer-tracking/configs
- PATCH /api/ai/cross-layer-tracking/configs/{config_id}
- DELETE /api/ai/cross-layer-tracking/configs/{config_id}
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import Index


# revision identifiers
revision = '019'
down_revision = '018'
branch_labels = None
depends_on = None


def upgrade():
    """Add cross-layer tracking configuration table"""

    # Create ai_cross_layer_tracking_configs table
    op.create_table(
        'ai_cross_layer_tracking_configs',
        sa.Column('id', sa.String(50), primary_key=True, nullable=False),
        sa.Column('config_name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('layers', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('sampling_rate', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('retention_days', sa.Integer(), nullable=False, server_default='30'),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='active'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), onupdate=sa.text('now()'), nullable=False),
        sa.Column('config_metadata', sa.JSON(), nullable=True),
    )

    # Create indexes for ai_cross_layer_tracking_configs
    op.create_index('idx_cross_layer_tracking_enabled', 'ai_cross_layer_tracking_configs', ['enabled'])
    op.create_index('idx_cross_layer_tracking_status', 'ai_cross_layer_tracking_configs', ['status'])


def downgrade():
    """Remove cross-layer tracking configuration table"""

    # Drop indexes for ai_cross_layer_tracking_configs
    op.drop_index('idx_cross_layer_tracking_status', table_name='ai_cross_layer_tracking_configs')
    op.drop_index('idx_cross_layer_tracking_enabled', table_name='ai_cross_layer_tracking_configs')

    # Drop ai_cross_layer_tracking_configs table
    op.drop_table('ai_cross_layer_tracking_configs')
