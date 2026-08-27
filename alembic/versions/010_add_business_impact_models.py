# -*- coding: utf-8 -*-
"""add business impact models

Revision ID: 010_add_business_impact_models
Revises: 009_add_plugin_marketplace_models
Create Date: 2026-08-26 17:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import func

# revision identifiers, used by Alembic.
revision = '010'
down_revision = '009'
branch_labels = None
depends_on = None


def upgrade():
    # Create business_impact_analysis table
    op.create_table(
        'business_impact_analysis',
        sa.Column('id', sa.String(50), nullable=False),
        sa.Column('service_name', sa.String(200), nullable=False),
        sa.Column('analysis_type', sa.String(50), nullable=False, server_default='full'),
        sa.Column('time_range', sa.String(50), nullable=False, server_default='1h'),
        sa.Column('include_dependencies', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('include_ux_metrics', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('result', sa.JSON(), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=func.now(), onupdate=func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('idx_business_impact_analysis_service_name', 'service_name'),
        sa.Index('idx_business_impact_analysis_status', 'status'),
        sa.Index('idx_business_impact_analysis_created_at', 'created_at'),
    )

    # Create business_impact_dependencies table
    op.create_table(
        'business_impact_dependencies',
        sa.Column('id', sa.String(50), nullable=False),
        sa.Column('source_service', sa.String(200), nullable=False),
        sa.Column('target_service', sa.String(200), nullable=False),
        sa.Column('dependency_type', sa.String(50), nullable=False, server_default='api_call'),
        sa.Column('criticality', sa.String(50), nullable=False, server_default='medium'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=func.now(), onupdate=func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('idx_business_impact_dependencies_source', 'source_service'),
        sa.Index('idx_business_impact_dependencies_target', 'target_service'),
        sa.Index('idx_business_impact_dependencies_criticality', 'criticality'),
    )

    # Create business_impact_reports table
    op.create_table(
        'business_impact_reports',
        sa.Column('id', sa.String(50), nullable=False),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('service_names', sa.JSON(), nullable=False),
        sa.Column('time_range', sa.String(50), nullable=False, server_default='24h'),
        sa.Column('include_recommendations', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('summary', sa.JSON(), nullable=True),
        sa.Column('service_data', sa.JSON(), nullable=True),
        sa.Column('recommendations', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=func.now(), onupdate=func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('idx_business_impact_reports_title', 'title'),
        sa.Index('idx_business_impact_reports_created_at', 'created_at'),
    )


def downgrade():
    op.drop_table('business_impact_reports')
    op.drop_table('business_impact_dependencies')
    op.drop_table('business_impact_analysis')