"""Add capacity planning models

Revision ID: 004_add_capacity_planning_models
Revises: 003_add_asset_management_models
Create Date: 2026-08-26 10:45:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import func


# revision identifiers, used by Alembic.
revision = '004_add_capacity_planning_models'
down_revision = '003_add_asset_management_models'
branch_labels = None
depends_on = None


def upgrade():
    # Create capacity_plans table
    op.create_table(
        'capacity_plans',
        sa.Column('id', sa.String(20), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('resource_type', sa.String(50), nullable=False),
        sa.Column('service', sa.String(255), nullable=False),
        sa.Column('current_capacity', sa.Float(), nullable=False),
        sa.Column('projected_capacity', sa.Float(), nullable=False),
        sa.Column('unit', sa.String(50), nullable=False),
        sa.Column('horizon', sa.String(50), nullable=False),
        sa.Column('target_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('threshold', sa.Float(), nullable=False),
        sa.Column('recommended_action', sa.Text(), nullable=False),
        sa.Column('estimated_cost', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=func.now(), nullable=False),
        sa.Column('created_by', sa.String(50), nullable=False, server_default='system'),
        sa.Column('status', sa.String(50), nullable=False, server_default='draft'),
        sa.Column('plan_metadata', sa.JSON(), nullable=True),
        sa.Index('idx_capacity_plans_resource_type', 'resource_type'),
        sa.Index('idx_capacity_plans_service', 'service'),
        sa.Index('idx_capacity_plans_status', 'status'),
    )
    op.create_primary_key('pk_capacity_plans', 'capacity_plans', ['id'])

    # Create optimization_results table
    op.create_table(
        'optimization_results',
        sa.Column('id', sa.String(20), nullable=False),
        sa.Column('service', sa.String(255), nullable=False),
        sa.Column('resource_types', sa.JSON(), nullable=False),
        sa.Column('strategy', sa.String(50), nullable=False),
        sa.Column('current_usage', sa.JSON(), nullable=False),
        sa.Column('optimized_usage', sa.JSON(), nullable=False),
        sa.Column('savings', sa.Float(), nullable=False),
        sa.Column('implementation_steps', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=func.now(), nullable=False),
        sa.Column('created_by', sa.String(50), nullable=False, server_default='system'),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('opt_metadata', sa.JSON(), nullable=True),
        sa.Index('idx_optimization_results_service', 'service'),
        sa.Index('idx_optimization_results_status', 'status'),
    )
    op.create_primary_key('pk_optimization_results', 'optimization_results', ['id'])

    # Create rightsizing_recommendations table
    op.create_table(
        'rightsizing_recommendations',
        sa.Column('id', sa.String(20), nullable=False),
        sa.Column('service', sa.String(255), nullable=False),
        sa.Column('resource_type', sa.String(50), nullable=False),
        sa.Column('current_spec', sa.JSON(), nullable=False),
        sa.Column('recommended_spec', sa.JSON(), nullable=False),
        sa.Column('action', sa.String(50), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('priority', sa.String(50), nullable=False),
        sa.Column('estimated_monthly_savings', sa.Float(), nullable=False),
        sa.Column('performance_impact', sa.Text(), nullable=False),
        sa.Column('implementation_complexity', sa.String(50), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=func.now(), nullable=False),
        sa.Column('rec_metadata', sa.JSON(), nullable=True),
        sa.Index('idx_rightsizing_recommendations_service', 'service'),
        sa.Index('idx_rightsizing_recommendations_resource_type', 'resource_type'),
    )
    op.create_primary_key('pk_rightsizing_recommendations', 'rightsizing_recommendations', ['id'])


def downgrade():
    # Drop rightsizing_recommendations table
    op.drop_table('rightsizing_recommendations')

    # Drop optimization_results table
    op.drop_table('optimization_results')

    # Drop capacity_plans table
    op.drop_table('capacity_plans')
